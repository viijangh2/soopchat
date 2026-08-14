"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SoopChat = void 0;
const ws_1 = __importDefault(require("ws"));
const const_1 = require("../const");
const client_1 = require("../client");
const types_1 = require("./types");
const tls_1 = require("tls");
const https_1 = require("https");
const event_1 = require("./event");
class SoopChat {
    client;
    ws;
    chatUrl;
    liveDetail;
    cookie = null;
    options;
    handlers = [];
    pingIntervalId = null;
    lastError = null;
    constructor(options) {
        this.options = options;
        this.options.baseUrls = options.baseUrls ?? const_1.DEFAULT_BASE_URLS;
        this.client = options.client ?? new client_1.SoopClient({ baseUrls: options.baseUrls });
    }
    _connected = false;
    _entered = false;
    async connect() {
        if (this._connected) {
            this.errorHandling('Already connected');
        }
        if (this.options.login) {
            this.cookie = await this.client.auth.signIn(this.options.login.userId, this.options.login.password);
            this.liveDetail = await this.client.live.detail(this.options.streamerId, this.cookie);
        }
        else {
            this.liveDetail = await this.client.live.detail(this.options.streamerId);
        }
        if (this.liveDetail.CHANNEL.RESULT === 0) {
            throw this.errorHandling("Not Streaming now");
        }
        this.chatUrl = this.makeChatUrl(this.liveDetail);
        this.ws = new ws_1.default(this.chatUrl, ['chat'], { agent: this.createAgent() });
        this.ws.onopen = () => {
            const CONNECT_PACKET = this.getConnectPacket();
            this.ws.send(CONNECT_PACKET);
        };
        this.ws.onmessage = this.handleMessage.bind(this);
        this.startPingInterval();
        this.ws.onerror = (event) => {
            this.lastError = event?.message || event?.error?.message || 'WebSocket error';
        };
        this.ws.onclose = (event) => {
            this.disconnect({
                code: event?.code,
                reason: event?.reason,
                wasClean: event?.wasClean,
                error: this.lastError
            });
        };
    }
    async disconnect(detail = {}) {
        if (!this._connected) {
            return;
        }
        const receivedTime = new Date().toISOString();
        this.emit(event_1.SoopChatEvent.DISCONNECT, {
            streamerId: this.options.streamerId,
            receivedTime: receivedTime,
            code: detail.code,
            reason: detail.reason,
            wasClean: detail.wasClean,
            error: detail.error
        });
        this.stopPingInterval();
        this.ws?.close();
        this.ws = null;
        this._connected = false;
    }
    async sendChat(message) {
        if (!this.cookie?.AuthTicket) {
            this.errorHandling("No Auth");
            return false;
        }
        if (!this.ws)
            return false;
        if (!this._entered)
            await this.waitForEnter();
        const packet = `${types_1.ChatDelimiter.SEPARATOR.repeat(1)}${message}${types_1.ChatDelimiter.SEPARATOR.repeat(1)}0${types_1.ChatDelimiter.SEPARATOR.repeat(1)}`;
        this.ws.send(`${types_1.ChatDelimiter.STARTER}${types_1.ChatType.CHAT}${this.getPayloadLength(packet)}00${packet}`);
        return true;
    }
    on(event, handler) {
        const e = event;
        this.handlers[e] = this.handlers[e] || [];
        this.handlers[e].push(handler);
    }
    emit(event, data) {
        if (this.handlers[event]) {
            for (const handler of this.handlers[event]) {
                handler(data);
            }
        }
    }
    async handleMessage(data) {
        const receivedTime = new Date().toISOString();
        const packet = data.data.toString();
        this.emit(event_1.SoopChatEvent.RAW, Buffer.from(packet));
        const messageType = this.parseMessageType(packet);
        switch (messageType) {
            case types_1.ChatType.CONNECT:
                this._connected = true;
                const connect = this.parseConnect(packet);
                this.emit(event_1.SoopChatEvent.CONNECT, { ...connect, streamerId: this.options.streamerId, receivedTime: receivedTime });
                const JOIN_PACKET = this.getJoinPacket();
                this.ws.send(JOIN_PACKET);
                break;
            case types_1.ChatType.ENTER_CHAT_ROOM:
                const enterChatRoom = this.parseEnterChatRoom(packet);
                this.emit(event_1.SoopChatEvent.ENTER_CHAT_ROOM, { ...enterChatRoom, receivedTime: receivedTime });
                if (this.cookie?.AuthTicket) {
                    const ENTER_INFO_PACKET = this.getEnterInfoPacket(enterChatRoom.synAck);
                    this.ws.send(ENTER_INFO_PACKET);
                }
                this._entered = true;
                break;
            case types_1.ChatType.NOTIFICATION:
                const notification = this.parseNotification(packet);
                this.emit(event_1.SoopChatEvent.NOTIFICATION, { ...notification, receivedTime: receivedTime });
                break;
            case types_1.ChatType.CHAT:
                const chat = this.parseChat(packet);
                this.emit(event_1.SoopChatEvent.CHAT, { ...chat, receivedTime: receivedTime });
                break;
            case types_1.ChatType.VIDEO_DONATION:
                const videoDonation = this.parseVideoDonation(packet);
                this.emit(event_1.SoopChatEvent.VIDEO_DONATION, { ...videoDonation, receivedTime: receivedTime });
                break;
            case types_1.ChatType.TEXT_DONATION:
                const textDonation = this.parseTextDonation(packet);
                this.emit(event_1.SoopChatEvent.TEXT_DONATION, { ...textDonation, receivedTime: receivedTime });
                break;
            case types_1.ChatType.AD_BALLOON_DONATION:
                const adBalloonDonation = this.parseAdBalloonDonation(packet);
                this.emit(event_1.SoopChatEvent.AD_BALLOON_DONATION, { ...adBalloonDonation, receivedTime: receivedTime });
                break;
            case types_1.ChatType.EMOTICON:
                const emoticon = this.parseEmoticon(packet);
                this.emit(event_1.SoopChatEvent.EMOTICON, { ...emoticon, receivedTime: receivedTime });
                break;
            case types_1.ChatType.VIEWER:
                const viewer = this.parseViewer(packet);
                this.emit(event_1.SoopChatEvent.VIEWER, { ...viewer, receivedTime: receivedTime });
                break;
            case types_1.ChatType.SUBSCRIBE:
                const subscribe = this.parseSubscribe(packet);
                this.emit(event_1.SoopChatEvent.SUBSCRIBE, { ...subscribe, receivedTime: receivedTime });
                break;
            case types_1.ChatType.EXIT:
                const exit = this.parseExit(packet);
                this.emit(event_1.SoopChatEvent.EXIT, { ...exit, receivedTime: receivedTime });
                break;
            case types_1.ChatType.DISCONNECT:
                await this.disconnect();
                break;
            default:
                const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
                this.emit(event_1.SoopChatEvent.UNKNOWN, parts);
                break;
        }
    }
    parseConnect(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, username, syn] = parts;
        return { username: username, syn: syn };
    }
    parseEnterChatRoom(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , streamerId, , , , , synAck] = parts;
        return { streamerId: streamerId, synAck: synAck };
    }
    parseSubscribe(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, to, from, fromUsername, amount, , , , tier] = parts;
        return { to: to, from: from, fromUsername: fromUsername, amount: amount, tier: tier };
    }
    parseAdBalloonDonation(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , to, from, fromUsername, , , , , , amount, fanClubOrdinal] = parts;
        return { to: to, from: from, fromUsername: fromUsername, amount: amount, fanClubOrdinal: fanClubOrdinal };
    }
    parseVideoDonation(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , to, from, fromUsername, amount, fanClubOrdinal] = parts;
        return { to: to, from: from, fromUsername: fromUsername, amount: amount, fanClubOrdinal: fanClubOrdinal };
    }
    parseViewer(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        if (parts.length > 4) {
            return { userId: this.getViewerElements(parts) };
        }
        else {
            const [, userId] = parts;
            return { userId: [userId] };
        }
    }
    parseExit(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , userId, username] = parts;
        return { userId: userId, username: username };
    }
    parseEmoticon(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , , stickerPackId, emoticonIndex, , userId, username] = parts;
        return { userId: userId, username: username, emoticonId: stickerPackId, emoticonIndex: emoticonIndex };
    }
    parseTextDonation(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, to, from, fromUsername, amount, fanClubOrdinal] = parts;
        return { to: to, from: from, fromUsername: fromUsername, amount: amount, fanClubOrdinal: fanClubOrdinal };
    }
    parseNotification(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, , , , notification] = parts;
        return { notification: notification };
    }
    parseChat(packet) {
        const parts = packet.split(types_1.ChatDelimiter.SEPARATOR);
        const [, comment, userId, , , , username] = parts;
        return { userId: userId, comment: comment, username: username };
    }
    parseMessageType(packet) {
        if (!packet.startsWith(types_1.ChatDelimiter.STARTER)) {
            throw this.errorHandling("Invalid data: does not start with STARTER byte");
        }
        if (packet.length >= 5) {
            return packet.substring(2, 6);
        }
        throw this.errorHandling("Invalid data: does not have any data for opcode");
    }
    startPingInterval() {
        if (this.pingIntervalId) {
            clearInterval(this.pingIntervalId);
        }
        this.pingIntervalId = setInterval(() => this.sendPing(), 60000);
    }
    stopPingInterval() {
        if (this.pingIntervalId) {
            clearInterval(this.pingIntervalId);
            this.pingIntervalId = null;
        }
    }
    sendPing() {
        if (!this.ws)
            return;
        const packet = this.getPacket(types_1.ChatType.PING, types_1.ChatDelimiter.SEPARATOR);
        this.ws.send(packet);
    }
    makeChatUrl(detail) {
        return `wss://${detail.CHANNEL.CHDOMAIN.toLowerCase()}:${Number(detail.CHANNEL.CHPT) + 1}/Websocket/${this.options.streamerId}`;
    }
    getByteSize(input) {
        return Buffer.byteLength(input, 'utf-8');
    }
    getPayloadLength(packet) {
        return this.getByteSize(packet).toString().padStart(6, '0');
    }
    createAgent() {
        const options = {};
        const secureContext = (0, tls_1.createSecureContext)(options);
        return new https_1.Agent({
            secureContext,
            rejectUnauthorized: false
        });
    }
    getViewerElements(array) {
        return array.filter((_, index) => index % 2 === 1);
    }
    getConnectPacket() {
        let payload = `${types_1.ChatDelimiter.SEPARATOR.repeat(3)}16${types_1.ChatDelimiter.SEPARATOR}`;
        if (this.cookie?.AuthTicket) {
            payload = `${types_1.ChatDelimiter.SEPARATOR.repeat(1)}${this.cookie?.AuthTicket}${types_1.ChatDelimiter.SEPARATOR.repeat(2)}16${types_1.ChatDelimiter.SEPARATOR}`;
        }
        return this.getPacket(types_1.ChatType.CONNECT, payload);
    }
    getJoinPacket() {
        let payload = `${types_1.ChatDelimiter.SEPARATOR}${this.liveDetail.CHANNEL.CHATNO}`;
        if (this.cookie) {
            payload += `${types_1.ChatDelimiter.SEPARATOR}${this.liveDetail.CHANNEL.FTK}`;
            payload += `${types_1.ChatDelimiter.SEPARATOR}0${types_1.ChatDelimiter.SEPARATOR}`;
            const log = {
                set_bps: this.liveDetail.CHANNEL.BPS,
                view_bps: this.liveDetail.CHANNEL.VIEWPRESET[0].bps,
                quality: 'normal',
                uuid: this.cookie._au,
                geo_cc: this.liveDetail.CHANNEL.geo_cc,
                geo_rc: this.liveDetail.CHANNEL.geo_rc,
                acpt_lang: this.liveDetail.CHANNEL.acpt_lang,
                svc_lang: this.liveDetail.CHANNEL.svc_lang,
                subscribe: 0,
                lowlatency: 0,
                mode: "landing"
            };
            const query = this.objectToQueryString(log);
            payload += `log${types_1.ChatDelimiter.ELEMENT_START}${query}${types_1.ChatDelimiter.ELEMENT_END}`;
            payload += `pwd${types_1.ChatDelimiter.ELEMENT_START}${types_1.ChatDelimiter.ELEMENT_END}`;
            payload += `auth_info${types_1.ChatDelimiter.ELEMENT_START}NULL${types_1.ChatDelimiter.ELEMENT_END}`;
            payload += `pver${types_1.ChatDelimiter.ELEMENT_START}2${types_1.ChatDelimiter.ELEMENT_END}`;
            payload += `access_system${types_1.ChatDelimiter.ELEMENT_START}html5${types_1.ChatDelimiter.ELEMENT_END}`;
            payload += `${types_1.ChatDelimiter.SEPARATOR}`;
        }
        else {
            payload += `${types_1.ChatDelimiter.SEPARATOR.repeat(5)}`;
        }
        return this.getPacket(types_1.ChatType.ENTER_CHAT_ROOM, payload);
    }
    getEnterInfoPacket(synAck) {
        const payload = `${types_1.ChatDelimiter.SEPARATOR}${synAck}${types_1.ChatDelimiter.SEPARATOR}0${types_1.ChatDelimiter.SEPARATOR}`;
        return this.getPacket(types_1.ChatType.ENTER_INFO, payload);
    }
    getPacket(chatType, payload) {
        const packetHeader = `${types_1.ChatDelimiter.STARTER}${chatType}${this.getPayloadLength(payload)}00`;
        return packetHeader + payload;
    }
    waitForEnter() {
        return new Promise((resolve) => {
            if (this._entered) {
                resolve();
                return;
            }
            const checkInterval = setInterval(() => {
                if (this._entered) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 500);
        });
    }
    errorHandling(message) {
        const error = new Error(message);
        console.error(error);
        return error;
    }
    objectToQueryString(obj) {
        return Object.entries(obj)
            .map(([key, value]) => `${types_1.ChatDelimiter.SPACE}&${types_1.ChatDelimiter.SPACE}${key}${types_1.ChatDelimiter.SPACE}=${types_1.ChatDelimiter.SPACE}${value}`)
            .join("");
    }
}
exports.SoopChat = SoopChat;
