import ws from 'k6/ws';
import http from 'k6/http';
import { check } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Scenario 1 teacher, 10000 students
export const options = {
  scenarios: {
    teacher: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 1,
      env: { ROLE: 'teacher' },
      gracefulStop: '10s',
    },
    students: {
      executor: 'ramping-arrival-rate',
      startRate: 10,       
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 10000,              
      stages: [
        { target: 500, duration: '30s' }, 
        { target: 2500, duration: '1m' }, 
        { target: 2500, duration: '1m' }, 
        { target: 0, duration: '30s' },   
      ],
      env: { ROLE: 'student' },
      startTime: '5s',
      gracefulStop: '30s',
    },
  },
};

const pdfPath = __ENV.PDF_FILE || './sample.pdf';
const samplePdf = open(pdfPath, 'b');

export function setup() {
  const wsUrl = __ENV.VITE_WS_URL || 'ws://localhost:6767';
  const apiUrl = __ENV.VITE_API_URL || 'http://localhost:6767';
  const classCode = `${randomString(6).toUpperCase()}`;

  console.log(`[SETUP] Creating room ${classCode}`);

  let setupData = {
    roomCode: classCode,
    totalSlides: 0,
    hostSessionId: null
  };

  ws.connect(wsUrl, null, function (socket) {
    socket.on('open', () => {
      socket.send(JSON.stringify({ event: 'connection:init', data: {} }));
    });

    socket.on('message', (e) => {
      const msg = JSON.parse(e);

      if (msg.event === 'connection:assigned') {
        setupData.hostSessionId = msg.data.session_id;
        socket.send(JSON.stringify({
          event: 'classroom:create',
          data: { class_code: classCode },
        }));
      } else if (msg.event === 'classroom:created') {
        const res = http.post(`${apiUrl}/upload/${classCode}/pdf`, samplePdf, {
          headers: { 'Content-Type': 'application/octet-stream' },
          timeout: '120s',
        });
        check(res, { 'upload ok': (r) => r.status === 200 });
        if (res.status !== 200) socket.close();
      } else if (msg.event === 'slides:ready') {
        setupData.totalSlides = msg.data.total_slides;
        console.log(`[SETUP] Slides ready (${setupData.totalSlides} slides).`);
        socket.close();
      } else if (msg.event === 'classroom:error' || msg.event === 'error') {
        console.error(`[SETUP] Error: ${msg.data?.message}`);
        socket.close();
      }
    });

    socket.setTimeout(() => socket.close(), 120000);
  });

  return setupData;
}

function teacherBroadcast(data) {
  const wsUrl = __ENV.VITE_WS_URL || 'ws://127.0.0.1:6767';
  let slide = 1;

  ws.connect(wsUrl, null, function (socket) {
    socket.on('open', () => {
      socket.send(JSON.stringify({ event: 'connection:init', data: { session_id: data.hostSessionId } }));
    });

    socket.on('message', (e) => {
      const msg = JSON.parse(e);
      if (msg.event === 'connection:assigned') {
        socket.send(JSON.stringify({
          event: 'classroom:sync',
          data: { class_code: data.roomCode },
        }));
      } else if (msg.event === 'classroom:state_sync') {
        socket.setInterval(() => {
          socket.send(JSON.stringify({
            event: 'slides:change',
            data: { class_code: data.roomCode, slide_number: slide },
          }));
          slide = (slide % data.totalSlides) + 1;
        }, 5000);
      }
    });

    socket.setTimeout(() => {
      console.log('[TEACHER] Test ended.');
      socket.close();
    }, 400000); 
  });
}

function studentJoiner(data) {
  const wsUrl = __ENV.VITE_WS_URL || 'ws://localhost:6767';
  const studentName = `Student-${randomString(4)}`;

  ws.connect(wsUrl, null, function (socket) {
    socket.on('open', () => {
      socket.send(JSON.stringify({ event: 'connection:init', data: {} }));
    });

    socket.on('message', (e) => {
      const msg = JSON.parse(e);
      if (msg.event === 'connection:assigned') {
        socket.send(JSON.stringify({
          event: 'classroom:join',
          data: { class_code: data.roomCode, student_name: studentName },
        }));
      } else if (msg.event === 'classroom:joined') {
      } else if (msg.event === 'classroom:error' || msg.event === 'error') {
        socket.close(); 
      }
    });

    socket.setInterval(() => {
      socket.ping();
    }, 30000);
  });
}

export default function (data) {
  if (!data || !data.roomCode) {
    console.error('Setup data missing!');
    return;
  }
  if (__ENV.ROLE === 'teacher') {
    teacherBroadcast(data);
  } else {
    studentJoiner(data);
  }
}