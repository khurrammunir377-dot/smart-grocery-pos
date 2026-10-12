const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const http = require("http");
const pino = require("pino");

const PORT = process.env.PORT || 5005;
let sock = null;
let isConnected = false;

process.on("uncaughtException", (err) => {
    console.error("⚠️ [Handled Exception]:", err.message);
});
process.on("unhandledRejection", (reason) => {
    console.error("⚠️ [Handled Rejection]:", reason);
});

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState("wa_auth_session");

    sock = makeWASocket({
        logger: pino({ level: "silent" }),
        printQRInTerminal: false,
        auth: state,
        shouldIgnoreJid: (jid) => jid === "status@broadcast" || jid.endsWith("@broadcast"),
        syncFullHistory: false
    });

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log("\n=================================");
            console.log("اپنے واٹس ایپ سے یہ QR کوڈ اسکین کریں:");
            console.log("=================================\n");
            qrcode.generate(qr, { small: true });
        }
        if (connection === "close") {
            isConnected = false;
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`⚠️ کنکشن بند ہوا۔ ری کنیکٹ ہو رہا ہے... (${shouldReconnect})`);
            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 3000);
            }
        } else if (connection === "open") {
            isConnected = true;
            console.log("\n==========================================");
            console.log("✅ واٹس ایپ گیٹ وے کامیابی سے لائیو اور منسلک ہے!");
            console.log(`🎯 پورٹ ${PORT} پر HTTP کالز کے لیے تیار ہے۔`);
            console.log("==========================================\n");
        }
    });

    sock.ev.on("creds.update", saveCreds);
}

connectToWhatsApp();

// خالص Native HTTP Server (جو ونڈوز پر کبھی ساکٹ ڈراپ نہیں کرتا)
const server = http.createServer(async (req, res) => {
    res.setHeader("Content-Type", "application/json");

    if (req.method === "GET" && req.url === "/ping") {
        console.log("📡 Ping موصول ہوئی!");
        res.writeHead(200);
        return res.end(JSON.stringify({ status: "ok", connected: isConnected }));
    }

    if (req.method === "POST" && req.url === "/send-message") {
        let body = "";
        req.on("data", chunk => { body += chunk.toString(); });
        req.on("end", async () => {
            try {
                const data = JSON.parse(body || "{}");
                const phone = (data.phone || "").toString().replace(/[^0-9]/g, "");
                const message = data.message || "";

                console.log(`📥 میسج کی درخواست موصول ہوئی برائے: +${phone}`);

                if (!sock || !isConnected) {
                    res.writeHead(503);
                    return res.end(JSON.stringify({ success: false, error: "WhatsApp not connected yet" }));
                }

                if (!phone || phone.length < 8) {
                    res.writeHead(400);
                    return res.end(JSON.stringify({ success: false, error: "Invalid phone number" }));
                }

                const jid = `${phone}@s.whatsapp.net`;
                await sock.sendMessage(jid, { text: message });

                console.log(`✅ [کامیابی] میسج گاہک کو چلا گیا: +${phone}`);
                res.writeHead(200);
                return res.end(JSON.stringify({ success: true, phone }));
            } catch (err) {
                console.error("❌ خرابی:", err.message);
                res.writeHead(500);
                return res.end(JSON.stringify({ success: false, error: err.message }));
            }
        });
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: "Not Found" }));
});

server.listen(PORT, "127.0.0.1", () => {
    console.log(`🚀 واٹس ایپ HTTP سرور پورٹ ${PORT} پر کامیابی سے شروع ہو گیا: http://127.0.0.1:${PORT}`);
});
