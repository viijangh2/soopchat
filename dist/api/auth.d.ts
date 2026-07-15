import { SoopClient } from "../client";
export interface Cookie {
    AbroadChk: string;
    AbroadVod: string;
    AuthTicket: string;
    BbsTicket: string;
    RDB: string;
    UserTicket: string;
    _au: string;
    _au3rd: string;
    _ausa: string;
    _ausb: string;
    isBbs: Number;
}
export declare class SoopAuth {
    private client;
    constructor(client: SoopClient);
    signIn(userId: string, password: string, baseUrl?: string): Promise<Cookie>;
}
