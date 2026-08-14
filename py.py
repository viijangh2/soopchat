# @title SOOP 채팅기
import os
import subprocess

# -------------------------------------------------------------
# 1. 환경 및 패키지 설치 여부 체크 & 최초 1회 자동 설치
# -------------------------------------------------------------
target_dir = "/content/soop_ex"

if not os.path.exists(os.path.join(target_dir, "node_modules")):
    print("🔄 최초 1회 환경 설정 및 패키지 설치를 시작합니다... (약 2~4분 소요)")

    setup_cmd = (
        "cd /content && "
        "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1 && "
        "sudo apt-get install -y nodejs > /dev/null 2>&1 && "
        "mkdir -p soop_ex && cd soop_ex && "
        "npm init -y > /dev/null 2>&1 && "
        "npm install git+https://github.com/viijangh2/soopchat.git"
    )

    result = subprocess.run(setup_cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Node.js 및 soopchat 패키지 설치 완료!")
    else:
        print("❌ 패키지 설치 중 오류 발생:")
        print(result.stderr)
else:
    print("⚡ 이미 설치되어 있습니다. 설치 과정을 건너뛰고 실행합니다.")

os.chdir(target_dir)

print(f"\n📍 현재 작업 경로: {os.getcwd()}")
print("🚀 파이썬 메인 코드를 실행합니다.")

import os
import json
import queue
import subprocess
import threading
import time
from google.colab import output
from IPython.display import HTML, display

# 1. 기존 프로세스 전역 정리
os.system("pkill -f bridge_full.cjs")

# 2. Node.js 브릿지 파일
bridge_code = r"""
// bridge_full.cjs
const { SoopClient, SoopChatEvent } = require('soop-extension');

async function start() {
    const [userId, password, streamerId] = process.argv.slice(2);
    const client = new SoopClient();
    const loginConfig = (userId && password) ? { userId, password } : null;

    function send(tag, user, content, isStreamer = false, meta = {}) {
        try {
            console.log(JSON.stringify({ tag, user, content, isStreamer, ...meta }));
        } catch(e) {}
    }

    function formatDisconnectReason(res = {}) {
        const parts = [];
        if (res.source) parts.push(`source: ${res.source}`);
        if (res.code !== undefined && res.code !== null) parts.push(`close code ${res.code}`);
        if (res.reason) parts.push(`reason: ${res.reason}`);
        if (res.wasClean !== undefined) parts.push(`clean: ${res.wasClean ? 'yes' : 'no'}`);
        if (res.error) parts.push(`error: ${res.error}`);
        if (res.lastMessageType) parts.push(`last message: ${res.lastMessageType}`);
        return parts.length ? parts.join(' / ') : '종료 이벤트에 상세 정보가 없어 Colab 런타임 중단, 네트워크 유휴 종료, 또는 서버 측 무사유 종료 가능성이 있습니다.';
    }

    process.on('uncaughtException', (err) => {
        send('FATAL', 'Node.js', `예외로 브릿지가 종료됩니다: ${err.message}`, false, { stack: err.stack || '' });
        process.exit(1);
    });

    process.on('unhandledRejection', (reason) => {
        const message = reason && reason.message ? reason.message : String(reason);
        send('FATAL', 'Node.js', `비동기 오류로 브릿지가 종료됩니다: ${message}`, false, { stack: reason && reason.stack ? reason.stack : '' });
        process.exit(1);
    });

    const normalizeUserId = (id) =>
        String(id || '')
            .replace(/\(\d+\)$/, "")
            .trim()
            .toLowerCase();

    const targetStreamerId = normalizeUserId(streamerId);

    function processEvent(res, defaultTag, extractContent) {
        setImmediate(() => {
            const rawUserId = res.userId || res.fromUserId || res.writerId || (res.user && res.user.id) || '';
            const normalizedId = normalizeUserId(rawUserId);

            const isStreamer = normalizedId === targetStreamerId;
            //const isTestUser = normalizedId === "crimsxnlake";
            const isTestUser = false;

            const username = res.username || res.fromUsername || (res.user && res.user.nickname) || '시스템';
            const content = typeof extractContent === 'function' ? extractContent(res) : extractContent;

            send(defaultTag, username, content, isStreamer || isTestUser);
        });
    }

    let cookieJar = [];

    let loginResult = null;
    if (userId && password) {
        try {
            loginResult = await client.auth.signIn(userId, password);

            if (loginResult && typeof loginResult === 'object') {
                for (const [key, val] of Object.entries(loginResult)) {
                    if (typeof val === 'string') {
                        if (val.includes('=')) cookieJar.push(val.split(';')[0].trim());
                        else cookieJar.push(`${key}=${val}`);
                    }
                }
            } else if (typeof loginResult === 'string') {
                cookieJar.push(...loginResult.split(';').map(c => c.trim()));
            }

            if (client.auth && client.auth.ticket) {
                cookieJar.push(`PdboxTicket=${client.auth.ticket}`);
            }
            if (userId) {
                cookieJar.push(`uid=${userId}`);
            }
        } catch (e) {
            send('ERROR', '로그인 모듈', '로그인 시도 중 오류 발생: ' + e.message);
        }
    }
    cookieJar = [...new Set(cookieJar.filter(Boolean))];

    if (cookieJar.length > 0 && streamerId) {
        (async () => {
            try {
                const stationUrl = `https://api-channel.sooplive.com/v1.1/channel/${streamerId}/station`;
                const response = await fetch(stationUrl, {
                    method: "GET",
                    headers: {
                        "Cookie": cookieJar.join('; '),
                        "Accept": "application/json, text/plain, */*",
                        "Origin": "https://www.sooplive.co.kr",
                        "Referer": `https://ch.sooplive.co.kr/${streamerId}`,
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                });
                const resData = await response.json();
                const userAuth = resData.userAuth || {};
                const station = resData.station || {};

                let isSubscribe = userAuth.isSubscribe || false;
                let isFavorite = userAuth.isFavorite || false;
                let tierType = null;

                if (isSubscribe) {
                    try {
                        const subscribeUrl = `https://myapi.sooplive.com/api/subscribe`;
                        const subResponse = await fetch(subscribeUrl, {
                            method: "GET",
                            headers: {
                                "Cookie": cookieJar.join('; '),
                                "Accept": "application/json, text/plain, */*",
                                "Origin": "https://www.sooplive.co.kr",
                                "Referer": "https://www.sooplive.co.kr/",
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            }
                        });

                        const subText = await subResponse.text();

                        if (!subResponse.ok || !subText.trim().startsWith('{')) {
                            let errMsg = `인증 세션이 유실되었거나 접근 권한이 없습니다. (Status: ${subResponse.status})`;
                            if (subText && subText.includes('CORS')) {
                                errMsg = "CORS 보안 정책에 의해 요청이 차단되었습니다.";
                            } else if (subText && subText.includes('message')) {
                                try {
                                    const errJson = JSON.parse(subText);
                                    if (errJson.message) errMsg = `${errJson.message} (${errJson.code || -1})`;
                                } catch(e) {}
                            }
                            send('ERROR', '인증체크봇', `티어 조회 실패: ${errMsg}`);
                        }
                        else {
                            const subData = JSON.parse(subText);
                            if (subData && subData.code !== undefined && subData.code < 0) {
                                send('ERROR', '인증체크봇', `티어 조회 실패 (${subData.code}): ${subData.message || '세션 만료'}`);
                            }
                            else if (subData && Array.isArray(subData.data)) {
                                const targetInfo = subData.data.find(sub =>
                                    sub.user_id && sub.user_id.toLowerCase() === streamerId.toLowerCase()
                                );

                                if (targetInfo && targetInfo.tier_type !== undefined) {
                                    tierType = targetInfo.tier_type;
                                }
                            }
                        }
                    } catch (subErr) {
                        send('ERROR', '인증체크봇', '티어 조회 오류: ' + subErr.message);
                    }
                }

                send('AUTH_CHECK', station.userNick || streamerId, {
                    isSubscribe: isSubscribe,
                    isFavorite: isFavorite,
                    tierType: tierType
                });

            } catch (err) {
                send('ERROR', '인증체크봇', '구독여부 조회 중 서버 오류: ' + err.message);
            }
        })();
    }

    const soopChat = client.chat({
        streamerId: streamerId,
        login: loginConfig
    });

    try {
        await soopChat.connect();
        send('SYSTEM', '시스템', 'CONNECTED_SUCCESS');
    } catch (err) {
        send('FATAL', '시스템', err.message);
        process.exit(1);
    }

    soopChat.on(SoopChatEvent.CHAT, (res) => {
        processEvent(res, "CHAT", res.comment);
    });

    soopChat.on(SoopChatEvent.EMOTICON, (res) => {
        processEvent(res, "EMOTICON", (r) => `https://ogqmarket.img.sooplive.com/sticker/${r.emoticonId}/${r.emoticonIndex}.png`);
    });

    soopChat.on(SoopChatEvent.TEXT_DONATION, (res) => {
        processEvent(res, "DONATION", (r) => `${r.amount}별풍선 후원 🎁`);
    });

    soopChat.on(SoopChatEvent.VIDEO_DONATION, (res) => {
        processEvent(res, "DONATION", (r) => `${r.amount}영상 후원 🎬`);
    });

    soopChat.on(SoopChatEvent.AD_BALLOON_DONATION, (res) => {
        processEvent(res, "DONATION", (r) => `${r.amount}애드벌룬 후원 🎈`);
    });

    soopChat.on(SoopChatEvent.SUBSCRIBE, (res) => {
        processEvent(res, "SUBSCRIBE", (r) => `${r.to} 구독 ${r.amount}개월 (티어 ${r.tier}) 🎊`);
    });

    soopChat.on(SoopChatEvent.NOTIFICATION, (res) => {
        send('NOTE', '공지', res.notification.replace(/\\r?\\n/g, ' '));
    });

    soopChat.on(SoopChatEvent.DISCONNECT, (res) => {
        const reason = formatDisconnectReason(res);
        send('DISCONNECT', '시스템', `${res.streamerId} 방송 서버와 연결이 해제되었습니다. 원인: ${reason}`, false, {
            code: res.code,
            reason: res.reason || '',
            wasClean: res.wasClean,
            error: res.error || '',
            source: res.source || '',
            packet: res.packet || '',
            lastMessageType: res.lastMessageType || '',
            lastMessageAt: res.lastMessageAt || '',
            uptimeMs: res.uptimeMs
        });
        process.exit(0);
    });

    process.stdin.on('data', async (data) => {
        const msg = data.toString().trim();
        if (!msg || msg.toLowerCase() === 'exit') {
            process.exit(0);
        }
        try {
            await soopChat.sendChat(msg);
            send('MYSELF', '나', msg);
        } catch (e) {
            send('ERROR', '시스템', e.message);
        }
    });
}
start();
"""
with open("bridge_full.cjs", "w", encoding="utf-8") as f:
    f.write(bridge_code)

# 3. 파이썬 백엔드 시스템
ui_queue = queue.Queue()
process = None
active_proc_id = 0
proc_lock = threading.Lock()
auth_state = {"id": "", "pw": "", "streamer": ""}

st_list = {
    "ecvhao": "우왁굳", "inehine": "아이네", "jingburger1": "징버거",
    "lilpa0309": "릴파", "cotton1217": "주르르", "gosegu2": "고세구", "viichan6": "비챤"
}

def js_string(text): return json.dumps(str(text), ensure_ascii=False)
def js(code):
    try: output.eval_js(code)
    except: pass

def listen_node(proc, proc_id):
    while active_proc_id == proc_id:
        line = proc.stdout.readline()
        if not line: break

        line_str = line.strip()
        if not line_str: continue

        if line_str.startswith('{') and line_str.endswith('}'):
            try:
                data = json.loads(line_str)
                tag = data.get('tag')
                user = data.get('user')
                content = data.get('content')
                is_streamer = data.get('isStreamer', False) # 💡 isStreamer 파싱 추가
                meta = {k: data.get(k) for k in ('code', 'reason', 'wasClean', 'error', 'stack', 'source', 'packet', 'lastMessageType', 'lastMessageAt', 'uptimeMs') if k in data}

                if tag == 'AUTH_CHECK':
                    ui_queue.put(('chat', 'AUTH_CHECK', user, content, '', False))
                elif content == "CONNECTED_SUCCESS":
                    disp_name = st_list.get(auth_state["streamer"], auth_state["streamer"])
                    ui_queue.put(('status', f'🟢 {disp_name} 연결됨'))
                    ui_queue.put(('chat', 'SYSTEM', '', f'✅ [{disp_name}] 방송 서버 연동 성공', '', False))
                else:
                    # 💡 UI로 전달하는 튜플에 is_streamer 정보 전달
                    ui_queue.put(('chat', tag, user, content, data.get('userId', ''), is_streamer, meta))
            except: pass

    exit_code = proc.poll()
    if active_proc_id == proc_id and exit_code is not None and exit_code != 0:
        ui_queue.put(('status', f'🔴 Node.js 브릿지 종료됨 (exit {exit_code})'))
        ui_queue.put(('chat', 'FATAL', '시스템', f'Node.js 브릿지가 비정상 종료되었습니다. exit code: {exit_code}', '', False, {'code': exit_code}))

def boot_node():
    global process, active_proc_id
    with proc_lock:
        if process:
            try:
                process.terminate()
                process.wait(timeout=0.2)
            except:
                try: process.kill()
                except: pass

        while not ui_queue.empty():
            try: ui_queue.get_nowait()
            except queue.Empty: break

        active_proc_id += 1
        current_id = active_proc_id
        ui_queue.put(('status', '⏳ 연결 시도 중...'))

        process = subprocess.Popen(
            ["node", "bridge_full.cjs", auth_state["id"], auth_state["pw"], auth_state["streamer"]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        threading.Thread(target=listen_node, args=(process, current_id), daemon=True).start()

# 4. 코랩 콜백
def kernel_poll():
    chats = []
    status_text = None

    count = 0
    while not ui_queue.empty() and count < 150:
        item = ui_queue.get()
        count += 1
        if item[0] == 'chat':
            # 💡 JS 전송 딕셔너리에 isStreamer 명시적 지정
            chats.append({
                "tag": item[1],
                "user": item[2],
                "content": item[3],
                "userId": item[4] if len(item) > 4 else "",
                "isStreamer": item[5] if len(item) > 5 else False,
                "meta": item[6] if len(item) > 6 else {}
            })
        elif item[0] == 'status':
            status_text = item[1]

    if status_text:
        js(f"document.getElementById('statusText').innerText = {js_string(status_text)};")

    if chats:
        js(f"window.appendChatBatch({json.dumps(chats, ensure_ascii=False)})")

def kernel_connect(streamer, uid, upw):
    auth_state["streamer"] = streamer
    auth_state["id"] = uid
    auth_state["pw"] = upw
    boot_node()

def kernel_send(msg):
    global process
    if process and process.poll() is None:
        try:
            process.stdin.write(msg + "\n")
            process.stdin.flush()
        except: pass
    else:
        js("window.appendChatBatch([{'tag':'ERROR', 'user':'시스템', 'content':'서버에 연결되지 않았습니다.'}])")

for cb in ("kernel_poll", "kernel_connect", "kernel_send"):
    try: output.unregister_callback(cb)
    except: pass
output.register_callback('kernel_poll', kernel_poll)
output.register_callback('kernel_connect', kernel_connect)
output.register_callback('kernel_send', kernel_send)

# 5. 프론트엔드 UI
html_code = r"""
<style>
@keyframes chatSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.chat-line {
    animation: chatSlideIn 0.14s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    line-height: 1.45;
    word-break: break-all;
    padding: 2.2px 6px;
    border-radius: 4px;
    transition: background 0.15s;
}
.chat-line:hover { background: rgba(255,255,255,0.04); }

.streamer-sidebar {
    width: 0px;
    height: 100%;
    background: #141416;
    border-left: 0px solid transparent;
    transition: width 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-left 0.25s ease;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.streamer-sidebar.open {
    width: 260px;
    border-left: 1px solid #444;
}

.sidebar-header {
    padding: 12px;
    background: #2b2b30;
    border-bottom: 1px solid #444;
    font-size: 13px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #ffb74d;
    white-space: nowrap;
    flex-shrink: 0;
}

.sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12px;
    background: #111112;
}

.sidebar-handle {
    width: 14px;
    background: #2b2b30;
    border-left: 1px solid #444;
    border-right: 1px solid #444;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #ffb74d;
    font-size: 10px;
    user-select: none;
    transition: background 0.2s, color 0.2s;
    flex-shrink: 0;
}
.sidebar-handle:hover {
    background: #3a3a42;
    color: #fff;
}
</style>

<div id="chatWrapper" style="display: flex; width: fit-content; height: 760px; margin: 0; background: #1e1e22; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">

    <div style="width: 480px; display: flex; flex-direction: column; flex-shrink: 0; height: 100%; background: #18181b;">

        <div style="padding: 15px; background: #2b2b30; border-bottom: 1px solid #444; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0;">
            <div style="display: flex; gap: 6px;">
                <select id="selStreamer" onchange="onSelectChange()" style="padding: 6px; background: #141416; border: 1px solid #555; color: white; border-radius: 4px; font-weight: bold; width: 170px; cursor: pointer;">
                    <option value="ecvhao">우왁굳 (ecvhao)</option>
                    <option value="inehine">아이네 (inehine)</option>
                    <option value="jingburger1">징버거 (jingburger1)</option>
                    <option value="lilpa0309">릴파 (lilpa0309)</option>
                    <option value="cotton1217">주르르 (cotton1217)</option>
                    <option value="gosegu2">고세구 (gosegu2)</option>
                    <option value="viichan6" selected>비챤 (viichan6)</option>
                    <option value="custom">직접 입력 ✍️</option>
                </select>
                <input type="text" id="inStreamer" value="viichan6" style="flex:1; padding: 6px; background: #141416; border: 1px solid #555; color: white; border-radius: 4px;">
                <button onclick="doConnect()" style="padding: 6px 16px; background: #9146ff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">연결</button>
            </div>
            <div style="display: flex; gap: 6px;">
                <input type="text" id="inId" placeholder="내 SOOP ID (비로그인 시 공백)" style="flex:1; padding: 6px; background: #141416; border: 1px solid #555; color: white; border-radius: 4px; font-size: 12px;">
                <input type="password" id="inPw" placeholder="비밀번호" style="flex:1; padding: 6px; background: #141416; border: 1px solid #555; color: white; border-radius: 4px; font-size: 12px;">
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
                <div id="scrollIndicator" style="color: #00e676; font-weight: bold;">● 실시간 추적 중</div>
                <div id="statusText" style="color: #aaa; font-weight: bold;">⚪ 대기 중...</div>
            </div>
            <div id="disconnectReason" style="display:none; color:#ffb74d; background:rgba(255,183,77,0.08); border:1px solid rgba(255,183,77,0.25); border-radius:4px; padding:6px 8px; font-size:11px; line-height:1.4; white-space:pre-wrap;"></div>
        </div>

        <div id="chatBox" onmouseenter="setScrollLock(true)" onmouseleave="setScrollLock(false)" ontouchstart="setScrollLock(true)" style="flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 2px; font-size: 13px; background: #18181b;">
            <div style="color: #666; text-align: center; font-size: 12px;">💡 방송 서버에 연결되면 채팅이 시작됩니다.</div>
        </div>

        <div style="padding: 10px; background: #2b2b30; display: flex; gap: 6px; border-top: 1px solid #444; position: relative; flex-shrink: 0;">
            <input type="text" id="inMsg" placeholder="실시간 채팅 참여..." onkeypress="if(event.key==='Enter') doSend()" style="flex:1; padding: 8px; background: #141416; border: 1px solid #555; color: white; border-radius: 4px; outline: none;">
            <button onclick="doSend()" style="padding: 8px 16px; background: #9146ff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">전송</button>
            <button onclick="toggleEmojiPicker()" style="padding: 8px; background: #3a3a42; color: white; border: 1px solid #555; border-radius: 4px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center;">😀</button>

            <div id="emojiPicker" style="display: none; position: absolute; bottom: 60px; right: 1px; background: #252529; border: 1px solid #444; border-radius: 6px; padding: 10px; width: 240px; height: 150px; overflow-y: auto; z-index: 100; box-shadow: 0 -4px 12px rgba(0,0,0,0.5);">
                <div id="emojiGrid" style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px;"></div>
            </div>
        </div>
    </div>

    <div id="sidebarHandle" onclick="toggleStreamerSidebar()" class="sidebar-handle">▶</div>

    <div id="streamerSidebar" class="streamer-sidebar">
        <div class="sidebar-header">
            <span>★ 스트리머 채팅 기록</span>
            <button onclick="clearStreamerSidebar()" style="background: none; border: none; color: #aaa; cursor: pointer; font-size: 11px;">전체 삭제</button>
        </div>
        <div id="streamerChatBox" class="sidebar-content">
            <div style="color: #555; text-align: center; margin-top: 20px;">스트리머의 채팅이<br>여기에 따로 기록됩니다.</div>
        </div>
    </div>
</div>

<script>
let isMouseOverChat = false;
let currentUserIsSubscribe = false;
let currentUserTier = 0;
let currentStreamerId = "viichan6";

function setScrollLock(isLocked) {
    isMouseOverChat = isLocked;
    const indicator = document.getElementById('scrollIndicator');
    const box = document.getElementById('chatBox');

    if (isLocked) {
        indicator.innerText = "■ 스크롤 일시정지 (마우스 올려둠)";
        indicator.style.color = "#ffb74d";
    } else {
        indicator.innerText = "● 자동 스크롤 중";
        indicator.style.color = "#00e676";
        runCleanUp();
        box.scrollTop = box.scrollHeight;
    }
}

function toggleStreamerSidebar() {
    const sidebar = document.getElementById('streamerSidebar');
    const handle = document.getElementById('sidebarHandle');
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
        handle.innerText = '◀';
    } else {
        handle.innerText = '▶';
    }
}

function clearStreamerSidebar() {
    const box = document.getElementById('streamerChatBox');
    box.innerHTML = '<div style="color: #555; text-align: center; margin-top: 20px;">기록이 비워졌습니다.</div>';
}

document.addEventListener('touchstart', function(e) {
    const box = document.getElementById('chatBox');
    if (!box.contains(e.target)) { setScrollLock(false); }
}, {passive: true});

const EMOJI_BASE_URL = "https://static.file.sooplive.com/signature_emoticon/";

const streamerEmojiRepository = {
    "ecvhao": {
        "tier2": {
            "/2티어응원봉/":    "5642673f10986a03b.webp", "/공지/":        "4907674363387c163.webp", "/2티어난하/":     "1824673f10c24024d.webp",
            "/민수채찍/":      "5258673f10e119edb.webp", "/타닥민수/":      "4401673f11071b76e.webp", "/축하/":        "866867547da326a20.webp",
            "/도리치/":       "521367547e465f7c8.webp", "/대/":         "1990673f1635e9e67.png", "/팩트/":        "9589673e387f1cb00.png",
            "/황/":         "13426743623755e7b.webp", "/행동/":        "7186673f11d69388d.png", "/추/":         "5967673e0e0abfcc8.png",
            "/보/":         "491667547e8ab9fb0.png", "/Z/":         "592367547eaf783ef.png", "/지지/":        "4474673e0d556a02e.png",
            "/왼쪽어깨/":      "8731673c8fe9122c8.png", "/어깡두/":       "7921673c900b44641.png", "/오른쪽어깨/":     "9204673c901f07d25.png",
            "/왁두왼쪽눈/":     "2666673c9740a40e8.png", "/왁두미간/":      "9272673c975a98e35.png", "/왁두오른쪽눈/":    "6956673c97699a012.png",
            "/왁갈통/":       "8156673c9a1274ba4.png", "/지직두/":       "3090673cab95b9e30.png", "/킹애/":        "271267547e0c58792.png",
            "/4집/":        "267967547fc74d2d7.png", "/딸깍/":        "5879673e0dce159a0.png", "/돚하/":        "5018673e0d79e5def.png",
            "/오/":         "5170673e0e2fe2525.png", "/얼차려2/":      "4262673f17016d266.png", "/낭만/":        "6309673e38982b5a7.png",
            "/풍선환/":       "83006772cac5db2a6.webp", "/반찬각/":       "2546673e394219c22.png", "/감다살/":       "6930673f12041f7e0.png",
            "/감다뒤/":       "7348673f124683c75.png", "/택티컬/":       "12006754804d5c228.png", "/수듄/":        "3653673f13eacf1a4.png",
            "/트롤/":        "829967507f0acd676.png", "/히키킹웃음/":     "33626743669c97be9.png", "/각성두/":       "86956750805948a9c.png",
            "/육광천/":       "30496772cb08ea1c9.webp"
        },
        "tier1": {
            "/응원티콘/":      "273465f0472b81d38.webp", "/아리가또또또/":    "909765f9d8402b7c2.webp", "/댄스팬치/":      "175567547f30f0378.webp",
            "/허쉬두/":       "920765f3216b0155d.webp", "/인사팬치/":      "197365f321eadd043.webp", "/팬치공감/":      "6517673f15cb5c4bb.webp",
            "/즙/":         "819765f9d9b6526ae.webp", "/왁하/":        "850865f9d9a64a4d8.png", "/정상화/":       "5477674365f0db8bf.png",
            "/빡팬치/":       "834665f048e7e4ca3.png", "/ak팬치/":      "774065f04a3e25532.webp", "/벌/":         "228565f049adbbb00.png",
            "/감자/":        "942665f321b0afeb2.png", "/군바/":        "781065f049157cb5d.png", "/젠/":         "6594673c98c7b3ab7.png",
            "/민수2/":       "8973675480db1b775.png", "/민수/":        "723965f320fd1b968.png", "/대음/":        "8182673f1841571c4.webp",
            "/대상현/":       "180467507ed26d2b5.webp", "/ㄷㄱㅈ/":       "729065f320a578c8e.png", "/밥/":         "251765f47fe9b5e0a.png",
            "/쩝쩝두/":       "979865f04a1b6d3be.png", "/명언두/":       "131465f3217f3a87d.png", "/슬슬/":        "730565f049680533d.png",
            "/기모찌/":       "901565f480255ff32.png", "/테헹두/":       "948665f049fac0ae5.png", "/늙병두/":       "237865f3213d79068.png",
            "/개빡두/":       "349765f049d839983.png", "/F/":         "169665f3226484257.png", "/놀람킹/":       "204167548159b0419.png",
            "/객관안/":       "483365f47fb155653.png", "/왁딩크/":       "64956743647300ade.png", "/왁린스만/":      "4053674364ce1ab19.png",
            "/그하/":        "3058673f14eb30e6d.png", "/고놀/":        "934865f9d81352f5e.png", "/왁뮤/":        "111165f9d73655499.png",
            "/형이봤/":       "9111673c94eba5dd3.png", "/새벽반/":       "3727673f187f83e8a.png", "/오뱅알/":       "588365f04896b2e26.png",
            "/숲바/":        "129267547d6e68110.png"
        }
    },
    "jingburger1": {
        "tier2": {
            "/징펀치/": "7625673a1c248345e.webp", "/열받셈무빙/": "8768674955c365bbe.webp", "/초롱초롱/": "5662674955e1947ac.webp",
            "/똑바로서라/": "83136749566dbf7ff.webp", "/슬쩍/": "3617674957e1aa703.png", "/굿모닝걸/": "9621674957f83d6b5.png",
            "/개빡친똥깡/": "58076749580c9f7b9.webp", "/반성중/": "2069674958523eec2.png", "/부가최고/": "815167495a3a5a3fa.webp",
            "/짝짝짝/": "490067495b1a11c62.webp", "/모뇨모뇨/": "784067495b2baab0a.webp", "/후비적/": "911267495b982e43a.png",
            "/신난부가/": "390767495bbed8788.webp", "/부가시/": "514967495c24c868b.png"
        },
        "tier1": {
            "/놀란버거/": "318765d745940146a.png", "/놀란강아지/": "798065d745e1cf87e.png", "/버거펀치/": "627165d745ee932e9.png",
            "/단비강아지/": "124065d9d65d13be2.webp", "/감자강아지/": "162065d9d66ade923.png", "/응원버거/": "718665d9d7c4e8f7e.webp",
            "/오열강아지/": "994765d9ec3b522be.png", "/로딩버거/": "894565db2302d332a.webp", "/썬구리버거/": "308365db8578085fa.png",
            "/귀여워/": "360565db899f5261c.png", "/흐뭇강아지/": "238465e3d9e57f5e3.png", "/강아지머리/": "515365e3da8f1384b.png",
            "/강아지엉덩이/": "451765e3dab3f41dd.png", "/엥/": "777765e3dc908e5e9.png", "/흠/": "192765e3dc9bec5ff.png",
            "/부자/": "705365e3e0cf86b7d.png", "/드가자/": "3035666a7a598c466.png", "/강아지몸통/": "3429666a7e99e8f68.png",
            "/스시버거1/": "2207666a83232b23a.png", "/스시버거2/": "8482666a832ed4091.png", "/스시버거3/": "1144666a833794791.png",
            "/하트버거/": "5871667148e0bab22.webp", "/너무좋아/": "781466a1204eb0a96.png", "/손뻗는/": "692866a1205d1c2fa.png",
            "/따봉손/": "239366a1208ecb18b.png", "/효과1/": "629466a1209c91ba3.png", "/효과2/": "486866a120a989dc8.png",
            "/싫어/": "602066a120b327012.png", "/빨간하트/": "431066a120bf4a9e6.png", "/말도안돼/": "767166a120cabcf48.png",
            "/뭐라는거야/": "918366a120ec2c1f9.png", "/느에/": "503566a120fa94751.png", "/노란하트/": "574166a1210586da5.png",
            "/좋아강아지/": "487066a1219b3a475.png", "/짱짱/": "931266a121c644921.png", "/신난다/": "488466a156ae2263c.webp",
            "/팝콘/": "938266a15f9ca023b.webp", "/고민/": "541966a29503a7bbb.webp", "/슬픈강아지/": "151666a295483e35a.webp",
            "/안아줘요/": "507366a295878026f.png"
        }
    },
    "lilpa0309": {
        "tier2": {
            "/대파/":        "9111674dc0d16685d.webp", "/복복복복2/":     "4671674dc10280403.webp", "/문열어/":       "9958674dc2144e237.webp",
            "/박쥐둠칫/":      "7139674dc22e7e0ea.webp", "/대파1/":       "18686761521fe5ea4.png", "/대파2/":       "37956761522d0ba64.png",
            "/대파3/":       "32456761523e29f01.png", "/자금지/":       "4032676152669f003.png", "/릴/":         "5213676152bb5e3ee.png",
            "/파/":         "4821676152cc1839d.png", "/대/":         "5811676152da2b9a0.png", "/니오/":        "638269821362a6f16.png",
            "/웨ㅔ/":        "7100698216495b5db.png", "/ㅔㅔ/":        "13196982167438680.png", "/ㅔ옹/":        "89846982168b980a8.png",
            "/느려2/":       "8898698214906fa84.png", "/후엉ㅠ/":       "490269821b13ac552.png", "/따봉파/":       "944569821c4c4c51f.png"
        },
        "tier1": {
            "/ㅋㅋㅋ/":       "490065f2bc3eec85a.png", "/합/":         "726165f2bc539d5b6.png", "/물음표/":       "746165f2bc6883c45.png",
            "/반짝/":        "654365f2bc7543581.png", "/갔나/":        "980165f2bc91e0968.png", "/릴하/":        "525865f2bd0c4cdd3.png",
            "/릴파하트/":      "850165f2bd41647a4.png", "/죽창1/":       "491265f2bda647372.png", "/죽창2/":       "392665f2bdb7431ee.png",
            "/응원2/":       "846066278ecb96a00.webp", "/응원3/":       "6043662e5456a9973.webp", "/나비다/":       "7667662792673cbf9.png",
            "/귀터진박쥐/":     "9262662e3a6824aad.png", "/릴파반짝눈1/":    "515367405ce297326.png", "/릴파반짝눈2/":    "319267405cf0bdf8d.png",
            "/릴파반짝눈3/":    "857667405d00a2573.png", "/너뭐야/":       "823567484a67d6133.png", "/엎드려/":       "266767484aa446e10.png",
            "/흐뭇/":        "834667484aed1f455.png", "/복복복복/":      "979267484b54dbd75.webp", "/둠칫둠칫/":      "328267484b6d943c6.webp",
            "/파칭/":        "8574674dc0af023f7.webp", "/잘가/":        "4333674dc181ede1a.webp", "/으아아아아앙/":    "8829674dc1d544cd1.webp",
            "/디코/":        "3932674dc29114c0d.png", "/릴트리버/":      "478967615070f15f9.webp", "/느려1/":       "49936761511b9a172.png",
            "/릴감자/":       "9162674dc256bedcf.png", "/ㅇ0ㅇ/":       "40486998b45332130.png", "/ㄲㅂ/":        "51936998b46dc073a.png",
            "/화/":         "11926999b1a66d28e.png", "/이/":         "26846999b1b86914f.png", "/팅/":         "44476999b1c374687.png",
            "/괜찮아/":       "70346999b3fd11109.png", "/치어리딩1/":     "60346999b4437e0c2.webp"
        }
    },
    "cotton1217": {
        "tier2": {
            "/광란댄스/":      "942267743ad051f65.webp", "/르르댄스/":      "273167502a7c3e097.webp", "/냠냠르르/":      "192167743b326e0a0.webp",
            "/주하하/":       "559567743bb11fe63.webp", "/화르르/":       "316867743bd188adb.webp"
        },
        "tier1": {
            "/르르하트/":      "289565d1e6674eef1.png", "/주폭펀치/":      "640665d1e69b29b48.png", "/주돈1/":       "385865d1e6c348a3e.png",
            "/주돈2/":       "692165d1e6ce3d634.png", "/주돈3/":       "944765d1e6d864fb7.png", "/빤히/":        "684265db6bb509c98.png",
            "/앵그리주폭/":     "786565d1e78f3683b.webp", "/르르응원/":      "262365d25c3beb5d5.webp", "/주폭댄스/":      "292965d25c5d8e6b0.webp",
            "/흐뭇주폭/":      "908565d25cb89d944.png", "/빡침주폭/":      "852965d25ce3d3ada.png", "/허걱주폭/":      "892865db6b89a4d7c.png",
            "/응원주폭/":      "398065db6bc8384a3.webp", "/따봉/":        "956065db6be3c26d6.png", "/멍청/":        "251465db6c06439d9.webp",
            "/대르르/":       "3832660da6ae7bf2f.png", "/우는주폭/":      "9287660da7b9673f8.png", "/쓰담/":        "740767502907ab57e.webp",
            "/주댄스/":       "4910675029151f85c.webp", "/땡깡폭도/":      "24126750292412337.webp", "/훈남폭도/":      "75206750294967017.png",
            "/난하르르/":      "51516750296d918df.png", "/주라임/":       "223967502978b2305.png", "/행복사/":       "25576750299d3cd94.png",
            "/부자폭도/":      "5683675029c404a7b.png", "/눈하트/":       "4098675029d1b3665.png", "/엥/":         "974667502a283a0b8.png",
            "/쿠궁1/":       "259067502a35249e4.png", "/쿠궁2/":       "101367502a41e4f65.png", "/쿠궁3/":       "868767502a4a908a8.png",
            "/르릇당/":       "682767743b55ac208.webp", "/머리박기/":      "826567743b6eaf0c7.png", "/호감/":        "158867743b7d80dcc.png",
            "/비호감/":       "505167743b8d557cf.png", "/포하/":        "198067743ba00a09e.png"
        }
    },
    "gosegu2": {
        "tier1": {
            "/품어/":        "623065f8d805b816d.png", "/쩝쩝구/":       "481565f8d821bd2a4.webp", "/감자/":        "659165f8d8358c67f.png",
            "/팡이제로투/":     "140165f956b5838bf.webp", "/버퍼균/":       "340565f956c790ca4.png", "/잘가/":        "39566604454dda3f2.png",
            "/세구라이드/":     "808365f957165b03f.webp", "/팝콘구/":       "722665f9572d01b58.png", "/어/":         "148265f9588acba89.png",
            "/난하/":        "5523660445667882c.png", "/고단/":        "893265f958cb1da90.png", "/고뱅알/":       "272065f958d762774.png",
            "/땡강균/":       "7681660445224e9ad.webp", "/빙글구/":       "774565f95903cc9df.webp", "/세구무빙/":      "75906603440fe4a62.webp",
            "/고하/":        "912265f9592917ad7.webp", "/센스봐라/":      "420665f9595acc6bf.png", "/깡/":         "450765f959726bdf8.webp",
            "/나이키왼/":      "691565f959db2a193.png", "/반짝눈왼/":      "215465f959fd0a5ab.png", "/나이키오/":      "332265f95a323958f.png",
            "/반짝눈오/":      "334965f95a414c3c1.png", "/입벌리기/":      "639565f95a5311ec4.png", "/고양이입술/":     "840665f95a5db4e31.png",
            "/그표정왼/":      "202665f95a6f32bc5.png", "/그표정오/":      "386465f95a7c3f1fd.png", "/놀란눈/":       "652065f95a97c431f.png",
            "/놀란눈오/":      "453465f95aa5d0611.png", "/크게벌린입/":     "554165f95abc73732.png", "/앙증입/":       "976265f95ac445bce.png",
            "/고오오/":       "68046603442b97600.png", "/ㄱㅇㅇ/":       "70036603446764ae3.png", "/ㅇㅈ세구/":      "5336660344814d936.png",
            "/하트구/":       "4549660344c30ae91.png", "/극대노/":       "73786603452a1ed59.png", "/빤/":         "34306603453ac85e1.png",
            "/폭소/":        "1471660345516f33c.png", "/미인입니다/":     "21166603455bbd392.png", "/오열/":        "82836603456aab760.png",
            "/응원구/":       "4610660446475d73d.webp"
        }
    },
    "viichan6": {
        "tier2": {
            "/락챤/":        "374167403a6a19067.webp", "/신나라니/":      "824367403a7994fba.webp", "/웃겨웃겨/":      "539067403ae968355.webp",
            "/쨘/":         "198567403b39da5b9.webp", "/얼빡챤/":       "939367403b5d30c93.png", "/싹싹/":        "346967403d8092865.webp",
            "/큰절/":        "365467403dedd2b4d.webp", "/챠/":         "3265691b65814723a.png", "/니/":         "5373691b65922c93f.png",
            "/볼/":         "4050691b65f834342.png", "/볼2/":        "7583691b6606c14ff.png", "/볼3/":        "8928691b661383dbb.png",
            "/트월킹/":       "5529691b6796840cb.webp", "/롱루이/":       "2578691b67a872901.png", "/롱루이2/":      "1042691b67b50d0e0.png",
            "/롱루이3/":      "4832691b67c3b2ad2.png"
        },
        "tier1": {
            "/국자라니/":      "224865c9fadf0c274.png", "/챠니잔다/":      "451565c9faf402785.png", "/따봉챤/":       "715965c9fb1085cde.png",
            "/챤하트/":       "371565c9fb989839b.png", "/라니팝콘/":      "160265c9fba492025.png", "/라니물음표/":     "471365c9fbb0f1883.png",
            "/라니삐짐/":      "307865c9fbc1a4293.png", "/라니화남/":      "156365c9fbcf65877.png", "/빛챤/":        "144465c9fbf73cd68.png",
            "/챠니응원봉/":     "832465ccbf279fff4.webp", "/쓰담챤/":       "883465fd4b3a60775.webp", "/챠니댄스/":      "1387667e4d8647d67.webp",
            "/신난라니/":      "1516667e4d9527d85.webp", "/챤하/":        "9866667e4db18a7f6.webp", "/ㄱㅇㅇ/":       "2838667e4dc0d89f3.png",
            "/안돼라니/":      "5502667e4deb3a0ec.png", "/드가자/":       "8460667e4e2168174.png", "/부끄러/":       "6481667e4e41493f2.png",
            "/망냥냥/":       "2706667e4e5625fea.png", "/미안해/":       "1250667e4e5fc78d2.png", "/쉿/":         "8853674039ecade4c.png",
            "/엥/":         "6791674039fc23295.png", "/댕빡챤/":       "511467403a29d9e5e.png", "/난하/":        "813767403a393392a.png",
            "/땡깡챤/":       "633367403aab4a702.webp", "/동공지진/":      "448867403ac125f4e.webp", "/라니울음/":      "772767403ba28af3a.png",
            "/비챤/":        "377567403bb92c4de.png", "/바보/":        "609967403bc5a19c8.png", "/조아/":        "303667403c060afe4.png",
            "/충성/":        "843767403c22c5b4b.png", "/납복/":        "110567403c3476775.png", "/꾸벅챤/":       "188867403d4a7e21c.webp",
            "/갔나/":        "948167403d6d4e9ec.webp", "/챤바/":        "2731691b663570dfd.png", "/빙라니/":       "8787691b66cebd207.png",
            "/시러/":        "8641691b66ea8f9be.png", "/루하/":        "2311691b66fa2a25a.png", "/헉챠니/":       "5050691b67647e07c.png",
            "/성불라니/":      "5650691b67e4d0b1e.webp"
        }
    }
};

let emojiMap = {};

function renderEmojiPicker(newMap) {
    if (newMap) { emojiMap = newMap; }
    const container = document.getElementById('emojiGrid');
    if (!container) return;
    container.innerHTML = '';

    const streamerId = currentStreamerId;
    const streamerRepo = streamerEmojiRepository[streamerId];
    if (!streamerRepo) return;

    for (const tierKey in streamerRepo) {
        const tagMatch = tierKey.match(/[0-9]+/);
        const requiredTier = tagMatch ? parseInt(tagMatch[0], 10) : 1;
        const emotes = streamerRepo[tierKey];

        for (const key in emotes) {
            const fileName = emotes[key];
            const img = document.createElement('img');
            img.src = EMOJI_BASE_URL + streamerId + "/" + fileName;
            img.title = `${key} (${requiredTier}티어)`;

            let imgStyle = "width:28px; height:28px; cursor:pointer; border-radius:4px; transition: all 0.2s;";
            if (!currentUserIsSubscribe || currentUserTier < requiredTier) {
                imgStyle += " cursor: not-allowed;";
            }

            img.style.cssText = imgStyle;
            img.onclick = () => addEmoji(key);
            container.appendChild(img);
        }
    }
}

const MAX_CHAT_COUNT = 2000;
const nameColors = [
    '#FF7043', '#FFB74D', '#FFF176', '#AEEA00', '#69F0AE',
    '#4ED8A3', '#26A69A', '#00E5FF', '#64B5F6', '#7B1FA2',
    '#BA68C8', '#FF80AB', '#FF8A80', '#E0E0E0', '#B0BEC5'
];

function getUserColor(username) {
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
    }
    return nameColors[Math.abs(hash) % nameColors.length];
}

function kernel(name, args=[]) {
    return google.colab.kernel.invokeFunction(name, args, {});
}

async function startPolling() {
    try { await kernel('kernel_poll'); } catch(e) {}
    setTimeout(startPolling, 80);
}
if (!window.hasPollingStarted) {
    startPolling();
    window.hasPollingStarted = true;
}

function toggleEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    picker.style.display = (picker.style.display === 'none' || picker.style.display === '') ? 'block' : 'none';
}

function addEmoji(emoji) {
    if (!currentUserIsSubscribe) {
        window.appendChatBatch([{'tag': 'ERROR', 'user': 'SYSTEM', 'content': '구독 중이 아닙니다. 이모티콘을 사용할 수 없습니다.'}]);
        return;
    }

    const emojiKey = emoji.startsWith('/') ? emoji : `/${emoji}/`;
    let streamerId = currentStreamerId;

    if (!streamerId && typeof streamerEmojiRepository !== 'undefined') {
        streamerId = Object.keys(streamerEmojiRepository).length > 0 ? Object.keys(streamerEmojiRepository)[0] : "viichan6";
    }

    const streamerRepo = streamerEmojiRepository[streamerId];
    if (streamerRepo) {
        let requiredTier = 1;
        let found = false;

        for (const tierKey in streamerRepo) {
            if (streamerRepo[tierKey][emojiKey]) {
                const tagMatch = tierKey.match(/[0-9]+/);
                requiredTier = tagMatch ? parseInt(tagMatch[0], 10) : 1;
                found = true;
                break;
            }
        }

        if (found && currentUserTier < requiredTier) {
            window.appendChatBatch([{'tag': 'ERROR', 'user': 'SYSTEM', 'content': `${requiredTier}티어 이상 구독자만 사용 가능한 이모티콘입니다. (내 등급: ${currentUserTier}티어)`}]);
            return;
        }
    }

    const el = document.getElementById('inMsg');
    if (el) { el.value += emojiKey; el.focus(); }
}

function onSelectChange() {
    const sel = document.getElementById('selStreamer');
    const inp = document.getElementById('inStreamer');
    if (sel.value === 'custom') { inp.value = ''; inp.focus(); }
    else { inp.value = sel.value; }
}

function doConnect() {
    const streamer = document.getElementById('inStreamer').value.trim();
    const uid = document.getElementById('inId').value.trim();
    const upw = document.getElementById('inPw').value.trim();
    if(!streamer) return alert("스트리머 ID를 입력하세요.");

    currentStreamerId = streamer;

    const selectedEmojis = streamerEmojiRepository[streamer] || {};
    renderEmojiPicker(selectedEmojis);

    document.getElementById('chatBox').innerHTML = '<div style="color: #888; text-align: center; font-size: 12px;">⏳ 실행 중...</div>';
    const reasonBox = document.getElementById('disconnectReason');
    if (reasonBox) { reasonBox.style.display = 'none'; reasonBox.textContent = ''; }
    isMouseOverChat = false;
    kernel('kernel_connect', [streamer, uid, upw]);
}

function doSend() {
    const el = document.getElementById('inMsg');
    const msg = el.value.trim();
    if(!msg) return;
    kernel('kernel_send', [msg]);
    el.value = '';
    document.getElementById('emojiPicker').style.display = 'none';
}

function runCleanUp() {
    const box = document.getElementById('chatBox');
    const overflow = box.children.length - MAX_CHAT_COUNT;
    for (let i = 0; i < overflow; i++) {
        if (box.firstChild) box.removeChild(box.firstChild);
    }
}

window.appendChatBatch = function(chatList) {
    const box = document.getElementById('chatBox');
    const fragment = document.createDocumentFragment();

    chatList.forEach(chat => {
        let processedText = chat.content;
        let data = {};

        if (chat.tag === 'AUTH_CHECK') {
            if (typeof chat.content === 'object' && chat.content !== null) {
                data = chat.content;
            } else if (typeof chat.content === 'string') {
                try { data = JSON.parse(chat.content); } catch (e) {}
            }

            const isSubscribeActive = data.isSubscribe || false;
            currentUserIsSubscribe = isSubscribeActive;

            const currentTier = data.tierType !== undefined ? data.tierType :
                                data.tier_type !== undefined ? data.tier_type : data.tier;

            if (isSubscribeActive && currentTier !== undefined && currentTier !== null) {
                const tierMatch = String(currentTier).match(/\d+/);
                currentUserTier = tierMatch ? parseInt(tierMatch[0], 10) : 1;
            } else {
                currentUserTier = 0;
            }

            let subDetail = '';
            if (isSubscribeActive) {
                subDetail = (currentTier !== undefined && currentTier !== null) ? ` (${currentTier}티어)` : '';
            }

            const isSub = isSubscribeActive ? `💖 구독 중${subDetail}` : '⚪ 미구독 상태';
            const isFavoriteActive = data.isFavorite || false;
            const isFav = isFavoriteActive ? '⭐ 즐겨찾기 완료' : '❌ 즐겨찾기 안 됨';

            const div = document.createElement('div');
            div.className = 'chat-line';
            div.style.cssText = "background: rgba(145, 70, 255, 0.15); border-left: 4px solid #9146ff; margin: 4px 0; padding: 6px 8px; font-size: 12px; border-radius: 2px;";
            div.innerHTML = `<span style="color:#b388ff; font-weight:bold;">🔐 [연동 세션 확인] ${chat.user}</span><br/>` +
                            `<span style="color:#efeff1;">└ 내 구독여부: <b>${isSub}</b></span><br/>` +
                            `<span style="color:#efeff1;">└ 즐겨찾기 상태: <b>${isFav}</b></span>`;

            fragment.appendChild(div);

            if (typeof renderEmojiPicker === 'function' && typeof streamerEmojiRepository !== 'undefined') {
                const newStreamerMap = streamerEmojiRepository[currentStreamerId];
                if (newStreamerMap) {
                    renderEmojiPicker(newStreamerMap);
                } else {
                    renderEmojiPicker();
                }
            }
            return;
        }

        if (typeof processedText === 'string') {
            if (typeof streamerEmojiRepository !== 'undefined' && currentStreamerId) {
                const streamerRepo = streamerEmojiRepository[currentStreamerId];
                if (streamerRepo) {
                    for (const tierKey in streamerRepo) {
                        const emotes = streamerRepo[tierKey];
                        for (const key in emotes) {
                            if (processedText.includes(key)) {
                                const fileName = emotes[key];
                                const fullUrl = EMOJI_BASE_URL + currentStreamerId + "/" + fileName;
                                const imgTag = `<img src="${fullUrl}" data-tag="${tierKey}" style="width:20px; height:20px; vertical-align:middle;" />`;
                                processedText = processedText.split(key).join(imgTag);
                            }
                        }
                    }
                }
            }
        }

        const div = document.createElement('div');
        div.className = 'chat-line';

        if (chat.tag === 'CHAT') {
            const nickColor = getUserColor(chat.user);
            if (chat.isStreamer) {
                div.innerHTML = `<span style="background:#9146ff; color:white; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:bold; margin-right:4px;">★</span><span style="color:#ffb74d; font-weight:bold;">${chat.user}:</span> <span style="color:#ffb74d;">${processedText}</span>`;
            } else {
                div.innerHTML = `<span style="color:${nickColor}; font-weight:bold;">${chat.user}:</span> <span style="color:#efeff1;">${processedText}</span>`;
            }
        }
        else if (chat.tag === 'EMOTICON') {
            const nickColor = getUserColor(chat.user);
            const nameSpan = chat.isStreamer
                ? `<span style="background:#9146ff; color:white; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:bold; margin-right:4px;">★</span><span style="color:#ffb74d; font-weight:bold;">${chat.user}:</span>`
                : `<span style="color:${nickColor}; font-weight:bold;">${chat.user}:</span>`;

            div.innerHTML = `${nameSpan} <img src="${processedText}" style="height:60px; vertical-align:middle;" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(document.createTextNode('[이모티콘]'))">`;
        }
        else if (chat.tag === 'DONATION') {
            div.innerHTML = `<span style="background:#ff4081; color:white; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:bold;">후원</span> <span style="color:#ff4081; font-weight:bold;">${chat.user}님:</span> <span style="color:#fff59d; font-weight:bold; background:rgba(255,64,129,0.1); padding:2px 4px; border-radius:4px;">${processedText}</span>`;
        }
        else if (chat.tag === 'SUBSCRIBE') {
            div.innerHTML = `<span style="background:#00e676; color:black; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:bold;">구독</span> <span style="color:#00e676; font-weight:bold;">${chat.user}님:</span> <span style="color:#00e676;">${processedText}</span>`;
        }
        else if (chat.tag === 'NOTE') {
            div.innerHTML = `<span style="background:#00b0ff; color:white; padding:1px 4px; border-radius:3px; font-size:10px;">공지</span> <span style="color:#00b0ff; font-weight:bold;">${processedText}</span>`;
        }
        else if (chat.tag === 'MYSELF') {
            div.innerHTML = `<span style="color:#81c784; font-weight:bold;">내 채팅:</span> <span style="color:#81c784;">${processedText}</span>`;
        }
        else if (chat.tag === 'DISCONNECT') {
            const meta = chat.meta || {};
            const detailLines = [
                `표시 시간: ${new Date().toLocaleString()}`,
                meta.code !== undefined ? `WebSocket close code: ${meta.code}` : null,
                meta.reason ? `서버 reason: ${meta.reason}` : null,
                meta.wasClean !== undefined ? `정상 종료 여부: ${meta.wasClean ? '예' : '아니오'}` : null,
                meta.error ? `오류: ${meta.error}` : null,
                meta.source ? `발생 지점: ${meta.source}` : null,
                meta.lastMessageType ? `마지막 수신 타입: ${meta.lastMessageType}` : null,
                meta.lastMessageAt ? `마지막 수신 시간: ${meta.lastMessageAt}` : null,
                meta.uptimeMs !== undefined ? `연결 유지 시간: ${Math.round(meta.uptimeMs / 1000)}초` : null,
                meta.packet ? `마지막 패킷 미리보기: ${meta.packet}` : null
            ].filter(Boolean);
            const reasonBox = document.getElementById('disconnectReason');
            if (reasonBox) {
                reasonBox.style.display = 'block';
                const hint = meta.source === 'soop-disconnect-packet'
                    ? '\n\n해석: WebSocket 자체 오류가 아니라 SOOP 채팅 서버가 연결 종료 패킷(0007)을 보낸 상황입니다. 방송 종료/채팅 서버 정책/중복 접속/세션 문제일 수 있습니다.'
                    : '';
                reasonBox.textContent = `🔎 최근 연결 끊김 원인\n${processedText}\n${detailLines.join('\n')}${hint}`;
            }
            div.innerHTML = `<span style="background:#ff9800; color:black; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:bold;">연결 끊김</span> <span style="color:#ffb74d;">${processedText}</span>`;
        }
        else if (chat.tag === 'ERROR' || chat.tag === 'FATAL') {
            const meta = chat.meta || {};
            const reasonBox = document.getElementById('disconnectReason');
            if (reasonBox && chat.tag === 'FATAL') {
                reasonBox.style.display = 'block';
                reasonBox.textContent = `🔎 브릿지 종료 원인\n${processedText}${meta.stack ? '\n' + meta.stack : ''}`;
            }
            div.innerHTML = `<span style="background:#eb0400; color:white; padding:1px 4px; border-radius:3px; font-size:10px;">오류</span> <span style="color:#ff4a4a;">${processedText}</span>`;
        }
        else {
            div.innerHTML = `<div style="text-align:center; color:#aaa; font-size:12px; background:rgba(255,255,255,0.05); padding:4px; border-radius:4px;">${processedText}</div>`;
        }

        // 스트리머 채팅일 경우 오른쪽 사이드바에 별도 기록
        if (chat.isStreamer) {
            const sBox = document.getElementById('streamerChatBox');

            if (sBox) {
                if (sBox.innerHTML.includes('text-align: center') || sBox.innerHTML.includes('margin-top: 20px')) {
                    sBox.innerHTML = '';
                }

                const sDiv = document.createElement('div');
                sDiv.className = 'chat-line';
                sDiv.style.borderLeft = '3px solid #ffb74d';
                sDiv.style.background = 'rgba(255, 183, 77, 0.05)';
                sDiv.style.marginBottom = '2px';

                const streamerContent = (chat.tag === 'EMOTICON')
                    ? `<img src="${processedText}" style="height:50px; vertical-align:middle;" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(document.createTextNode('[이모티콘]'))">`
                    : `<span style="color:#ffb74d;">${processedText}</span>`;

                sDiv.innerHTML = `<span style="color:#ffb74d; font-weight:bold;">${chat.user}:</span> ${streamerContent}`;

                sBox.appendChild(sDiv);
                sBox.scrollTop = sBox.scrollHeight;
            }
        }

        fragment.appendChild(div);
    });

    if (box) {
        box.appendChild(fragment);
        if (!isMouseOverChat) {
            runCleanUp();
            box.scrollTop = box.scrollHeight;
        }
    }
};
</script>
"""
display(HTML(html_code))
