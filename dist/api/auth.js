"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SoopAuth = void 0;
const const_1 = require("../const");
class SoopAuth {
    client;
    constructor(client) {
        this.client = client;
    }
    async signIn(userId, password, baseUrl = const_1.DEFAULT_BASE_URLS.soopAuthBaseUrl) {
        const formData = new FormData();
        formData.append("szWork", "login");
        formData.append("szType", "json");
        formData.append("szUid", userId);
        formData.append("szPassword", password);
        const response = await this.client.fetch(`${baseUrl}/app/LoginAction.php`, {
            method: "POST",
            body: formData
        });
        const setCookieHeader = response.headers.get("set-cookie");
        if (!setCookieHeader) {
            throw new Error("No set-cookie header found in response");
        }
        const getCookieValue = (name) => {
            const regex = new RegExp(`${name}=([^;]+)`);
            const match = setCookieHeader.match(regex);
            if (!match) {
                throw new Error(`Cookie "${name}" not found in set-cookie header`);
            }
            return match[1];
        };
        return {
            AbroadChk: getCookieValue("AbroadChk"),
            AbroadVod: getCookieValue("AbroadVod"),
            AuthTicket: getCookieValue("AuthTicket"),
            BbsTicket: getCookieValue("BbsTicket"),
            RDB: getCookieValue("RDB"),
            UserTicket: getCookieValue("UserTicket"),
            _au: getCookieValue("_au"),
            _au3rd: getCookieValue("_au3rd"),
            _ausa: getCookieValue("_ausa"),
            _ausb: getCookieValue("_ausb"),
            isBbs: Number(getCookieValue("isBbs"))
        };
    }
}
exports.SoopAuth = SoopAuth;
