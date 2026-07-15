"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SoopClient = void 0;
const api_1 = require("./api");
const const_1 = require("./const");
const chat_1 = require("./chat");
const api_2 = require("./api");
class SoopClient {
    options;
    live = new api_1.SoopLive(this);
    channel = new api_2.SoopChannel(this);
    auth = new api_1.SoopAuth(this);
    constructor(options = {}) {
        options.baseUrls = options.baseUrls || const_1.DEFAULT_BASE_URLS;
        options.userAgent = options.userAgent || const_1.DEFAULT_USER_AGENT;
        this.options = options;
    }
    get chat() {
        return (options) => {
            return new chat_1.SoopChat({
                client: this,
                baseUrls: this.options.baseUrls,
                ...options
            });
        };
    }
    fetch(url, options) {
        const headers = {
            "User-Agent": this.options.userAgent,
            ...(options?.headers || {})
        };
        return fetch(url, {
            headers: headers,
            ...options
        });
    }
}
exports.SoopClient = SoopClient;
