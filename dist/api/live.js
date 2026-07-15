"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SoopLive = exports.DEFAULT_REQUEST_BODY_FOR_LIVE_STATUS = void 0;
const const_1 = require("../const");
exports.DEFAULT_REQUEST_BODY_FOR_LIVE_STATUS = {
    'type': 'live',
    'pwd': '',
    'player_type': 'html5',
    'stream_type': 'common',
    'quality': 'HD',
    'mode': 'landing',
    'from_api': '0',
    'is_revive': false
};
class SoopLive {
    client;
    constructor(client) {
        this.client = client;
    }
    async detail(streamerId, cookie = null, options = exports.DEFAULT_REQUEST_BODY_FOR_LIVE_STATUS, baseUrl = const_1.DEFAULT_BASE_URLS.soopLiveBaseUrl) {
        const body = {
            bid: streamerId,
            ...(options || {})
        };
        const params = new URLSearchParams(Object.entries(body).reduce((acc, [key, value]) => {
            acc[key] = String(value);
            return acc;
        }, {}));
        return this.client.fetch(`${baseUrl}/afreeca/player_live_api.php?bjid=${streamerId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie && this.buildCookieString(cookie)
            },
            body: params.toString()
        })
            .then(response => response.json())
            .then(data => {
            return { CHANNEL: data["CHANNEL"] };
        });
    }
    buildCookieString(data) {
        return Object.entries(data)
            .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
            .join("; ");
    }
}
exports.SoopLive = SoopLive;
