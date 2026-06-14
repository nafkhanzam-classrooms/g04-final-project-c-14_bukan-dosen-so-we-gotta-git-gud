import ws from 'k6/ws';
import { check } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Scenario 1 Teacher, 1000 Students send quiz answer at the same time
export const options = {
  scenarios: {
    teacher: {
      executor: 'shared-iterations',
      vus: 1,
      iterations: 1,
      maxDuration: '2m',
      env: { ROLE: 'teacher' },
    },
    students: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 1000 }, 
        { duration: '1m', target: 1000 },  
        { duration: '15s', target: 0 },    
      ],
      env: { ROLE: 'student' },
      startTime: '2s', 
    },
  },
};

export function setup() {
  const classCode = `${randomString(6).toUpperCase()}`;
  console.log(`[SETUP] Target Room Code: ${classCode}`);
  return { roomCode: classCode };
}

export default function (data) {
  const wsUrl = __ENV.VITE_WS_URL || 'ws://localhost:6767';
  const role = __ENV.ROLE;

  ws.connect(wsUrl, null, function (socket) {
  
    socket.on('open', () => {
      socket.send(JSON.stringify({ event: 'connection:init', data: {} })); 
    });

    socket.on('message', (e) => {
      const msg = JSON.parse(e);

      if (role === 'teacher') {
        if (msg.event === 'connection:assigned') {
          socket.send(JSON.stringify({
            event: 'classroom:create',
            data: { class_code: data.roomCode },
          }));
        } 
        else if (msg.event === 'classroom:created') {
          console.log(`[TEACHER] Classroom ${data.roomCode} created. Waiting 20s for students to gather...`);
        
          socket.setTimeout(() => {
            console.log('[TEACHER] Firing quiz:start...');
            socket.send(JSON.stringify({
              event: 'quiz:start',
              data: { 
                class_code: data.roomCode, 
                question_id: 'q_01', 
                options: ['A', 'B', 'C', 'D'] 
              }, 
            }));
          }, 20000); 
        }
        else if (msg.event === 'quiz:answer_received') {
          console.log(`[TEACHER] Live Tracker Update: ${msg.data.total_answered} students answered.`);
        }
      } 
      
      else if (role === 'student') {
        if (msg.event === 'connection:assigned') {
          socket.send(JSON.stringify({
            event: 'classroom:join',
            data: { 
              class_code: data.roomCode, 
              student_name: `Student-${randomString(4)}` 
            }, 
          }));
        }
        else if (msg.event === 'quiz:started') { 
          const answers = ['A', 'B', 'C', 'D'];
          const randomAnswer = answers[Math.floor(Math.random() * answers.length)];
          
          socket.send(JSON.stringify({
            event: 'quiz:answer',
            data: { 
              class_code: data.roomCode, 
              question_id: msg.data.question_id, 
              answer: randomAnswer 
            }, 
          }));
        }
      }

      if (msg.event === 'classroom:error' || msg.event === 'error') {
        console.error(`[${role.toUpperCase()}] Server Error:`, msg.data);
        socket.close();
      }
    });

    socket.setTimeout(() => {
      console.log(`[${role.toUpperCase()}] Timeout reached. Closing connection.`);
      socket.close();
    }, 115000);
    
  });
}