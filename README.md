[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/90Mprfp5)
# Network Programming - Final Project [G04]

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Mohammed Lazuardi Yasfin               | 5025241139           | C          |
| Bintang Ilham Pabeta               | 5025241152           | C          |

## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```
https://youtu.be/GuyuJVKOk5A
```

## Penjelasan Program

### Deskripsi Aplikasi

CarbonFreeClass adalah platform kelas interaktif real-time yang memungkinkan pengajar (host) untuk membagikan presentasi (PDF/PPTX) dan memberikan kuis interaktif (pop quiz) kepada siswa secara langsung. Aplikasi ini mengedepankan komunikasi dua arah berlatensi rendah, gamifikasi dengan live leaderboard, dan sistem broadcasting event kelas secara sinkron.

### Quick Start

#### Development Environment

```
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

#### Production Environment

Pastikan `.env` yang sudah terisi sesuai `.env.example` berada di direktori yang sama.
```
docker compose -f compose.yaml -f compose.prod.yaml up --build
```

#### Multi-instance

```
docker compose -f compose.yaml -f compose.prod.yaml up --build --scale backend=3
```


### Arsitektur Sistem

```mermaid
flowchart TB
    subgraph Clients [Browser Clients]
        Host[Teacher<br/>Vue 3]
        Student[Students<br/>Vue 3]
    end

    subgraph InternalNetwork [Docker Network: proxy_net]
        
        subgraph Gateway [Gateway]
            Caddy[Caddy Reverse Proxy<br/>& Static File Server]
        end

        subgraph BackendCluster [Distributed Backend Cluster: backend]
            direction TB
            Backend1[Backend Instance 1<br/>Python websockets]
            Backend2[Backend Instance 2<br/>Python websockets]
            Backend3[Backend Instance 3<br/>Python websockets]
        end

        Worker[Worker Service<br/>Raw asyncio HTTP Server]
        Redis[(Redis<br/>State & Pub/Sub Broker)]
        Volume[(Shared Volume<br/>slides_volume)]
    end

    %% Client to Gateway
    Host -- "1. WSS <br/>2. HTTPS POST /upload/*" --> Caddy
    Student -- "1. WSS <br/>2. HTTPS GET /slides/*" --> Caddy

    %% Gateway Routing (Load Balancing)
    Caddy -- "WSS" --> Backend1
    Caddy -- "WSS" --> Backend2
    Caddy -- "WSS" --> Backend3

    Caddy -- "Route /upload/* (port 8080)" --> Worker
    Caddy -- "File Server /slides/*" --> Volume

    %% Backend Interactions
    Backend1 & Backend2 & Backend3 -- "Read/Write State" --> Redis
    Backend1 & Backend2 & Backend3 -- "Publish/Subscribe" --> Redis

    %% Worker Interactions
    Worker -- "Save generated<br/>WebP images" --> Volume
    Worker -- "Publish event<br/>(slides:ready)" --> Redis

    %% Styling
    classDef client fill:#d4edda,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef proxy fill:#fff3cd,stroke:#fbc02d,stroke-width:2px,color:#000;
    classDef backend fill:#cce5ff,stroke:#1976d2,stroke-width:2px,color:#000;
    classDef db fill:#f8d7da,stroke:#d32f2f,stroke-width:2px,color:#000;
    classDef vol fill:#e2e3e5,stroke:#6c757d,stroke-width:2px,color:#000;
    classDef cluster fill:none,stroke:#1976d2,stroke-width:2px,stroke-dasharray: 5 5;

    class Host,Student client;
    class Caddy proxy;
    class Backend1,Backend2,Backend3 backend;
    class Redis db;
    class Volume vol;
    class BackendCluster cluster;
```

Aplikasi ini menggunakan arsitektur terdistribusi yang terdiri dari beberapa node yang saling berkomunikasi melalui berbagai protokol jaringan:

- Frontend: Bertindak sebagai Client yang membuka koneksi persisten menggunakan WebSocket ke Backend, serta melakukan HTTP POST ke Worker untuk upload file dan HTTP GET ke Caddy untuk download slides.
- Backend: Bertindak sebagai WebSocket Server utama. Menangani ribuan koneksi konkuren, state management real-time (room, slides, leaderboard), serta melakukan broadcasting pesan.
- Worker: Bertindak sebagai Background Processor dan Custom HTTP Server. Bertugas menerima upload dokumen, mengubahnya menjadi gambar WebP secara asynchronous, lalu mengabari Backend via Redis.
- Redis: Bertindak sebagai In-Memory Database untuk state global dan sebagai Message Broker (Pub/Sub) untuk Inter-Process Communication (IPC) antar layanan.
- Caddy: Bertindak sebagai reverse proxy yang merutekan traffic dan load balancing WSS antara tiga backend instance.

### Implementasi

#### Komunikasi Full-Duplex secara Real-Time

Aplikasi menggunakan protokol WebSocket melalui pustaka `websockets` dan koneksi native WebSocket di frontend. Backend mengelola setiap koneksi dengan `WSConnectionManager`. Komponen ini bertanggung jawab untuk:

- Registrasi dan unregistrasi sesi dengan mapping `session_id` ke objek websocket.

- Mengimplementasikan beberapa connection reliability mechanism.

- Pembuatan sesi baru atau re-koneksi melalui metode `establish()` yang membaca frame pertama untuk mengambil `session_id` lama atau membuat token baru.

- Pengiriman pesan terstruktur dengan `send(event, session_id, data)` yang membungkus payload ke dalam WSMessage sebelum diubah ke JSON.


#### Concurrent Architecture

Backend dibangun di atas asyncio untuk menangani ribuan koneksi non‑blocking. Beberapa mekanisme konkurensi diterapkan:

- WebSocket server berjalan pada satu event loop, dengan handler async per koneksi.

- Rate limiting pada Redis menggunakan `RateLimitedRedis` yang membungkus perintah `execute` dengan `asyncio.Semaphore(max_concurrency=200)`. Ini mencegah terjadinya thundering herd saat banyak request simultan ke Redis.

- Worker service mengimplementasikan custom HTTP server di atas `asyncio.start_server` untuk menerima upload file. Worker mem-parsing header HTTP secara manual, membaca body, lalu menjalankan konversi PDF/PPTX ke WebP menggunakan sub‑proses pdftoppm dan cwebp secara concurrent.

#### Custom Protocol & Message Format

Di atas layer komunikasi WebSocket, aplikasi mendefinisikan Application-Level Protocol miliknya sendiri untuk menstandardisasi pertukaran pesan. Semua paket dibungkus dalam format envelope yang konsisten, yaitu 

```
{"event": "<prefix>:<action>", "data": { ... }}
```

Paket mentah yang masuk akan di-parse dan didistribusikan oleh komponen Event Router `WSEventRouter`. Pesan diteruskan ke handler spesifik (`ClassroomHandler`, `SlideHandler`, `QuizHandler`). Setiap payload divalidasi secara ketat menggunakan schema Pydantic untuk memastikan integritas tipe data sebelum diproses oleh service internal.

#### Connection Reliability

Backend mengimplementasikan beberapa mekanisme connection reliability yang terintegrasi di `WSConnectionManager` dan konfigurasi WebSocket server:

- Keep‑alive & deteksi half open: 
  Pada saat membuat WebSocket server, parameter `ping_interval=20` dan `ping_timeout=20` diberikan ke `websockets.serve`. Server secara otomatis mengirim ping setiap 20 detik. Apabila dalam 20 detik tidak ada pong, koneksi dianggap mati (TCP half‑open) dan ditutup guna mencegah kebocoran resource.

- Client reconnection: 
  Ketika klien (frontend) melakukan reconnect, ia mengirim frame pertama berisi `{"data": {"session_id": "xxx"}}`. Metode `establish()` di `WSConnectionManager` membaca frame tersebut, memverifikasi `session_id`, dan mengembalikan id yang sama (bukan membuat token baru). Setelah koneksi berhasil, klien mengirim event `classroom:sync` ke `ClassroomHandler`. Handler ini kemudian mengambil state ruang terbaru dari Redis dan mengirim balik `classroom:state_sync` yang berisi slide saat ini, total slide, daftar siswa, dan sebagainya.

- Duplicate login: 
  Jika sesi dengan `session_id` yang sama mencoba melakukan koneksi baru, `WSConnectionManager.register()` akan menutup koneksi lama dengan kode 4000 dan pesan `connection:replaced`, lalu menyimpan koneksi baru.

- Malformed packet mitigation:
  Setiap pesan yang masuk diproses oleh `process_raw_message()`. Jika decoding JSON gagal, fungsi `manager.record_error(session_id)` akan menambah counter error untuk sesi tersebut. Apabila counter mencapai `max_error_tolerance`, manager akan memanggil `kick()` yang menutup koneksi dengan kode 1008 (Policy Violation).

#### Multi-Instance Docker Deployment

Sistem dipaketkan menggunakan multi-stage Docker build dan dirancang dengan arsitektur terdistribusi:

- Caddy sebagai reverse proxy sekaligus load balancer WebSocket, mendistribusikan koneksi ke beberapa instance backend.

- Backend bersifat stateless. Seluruh data krusial (room state, TTL ruangan, leaderboard) disimpan secara terpusat di Redis.

- Inter‑Process Communication (IPC) menggunakan Redis Pub/Sub:

    - Worker setelah selesai konversi slide mempublish event `slides:ready` ke channel `room_events`.

    - Backend memiliki `RedisEventBus` yang melakukan subscribe ke channel yang sama dan memanggil `RoomEventHandler`. Event handler kemudian memperbarui total slides di Redis dan melakukan broadcast ke semua peserta ruang melalui `RoomBroadcastService`.

- Skalabilitas horizontal dengan `docker compose up --scale backend=3`, Caddy akan melakukan load balancing round‑robin dimana semua instance tetap sinkron karena membaca/menulis ke Redis yang sama.

## Screenshot Hasil

![](https://i.imgur.com/woKilpQ.png)

![](https://i.imgur.com/UHIXuj8.png)

![](https://i.imgur.com/S4MCQuH.png)

![](https://i.imgur.com/EnEbycC.png)

![](https://i.imgur.com/v7vIFww.png)

![](https://i.imgur.com/p5YfRTO.png)

![](https://i.imgur.com/HCQKVSW.png)

![](https://i.imgur.com/M0REkWR.png)

![](https://i.imgur.com/o2gF8Yp.png)

![](https://i.imgur.com/TWyatX0.png)

![](https://i.imgur.com/3W2OJwn.png)

![](https://i.imgur.com/dKSu3ls.png)

![](https://i.imgur.com/CnImpw1.png)

![](https://i.imgur.com/7G4RMpQ.png)

![](https://i.imgur.com/i6L7p13.png)