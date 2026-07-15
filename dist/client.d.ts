import { SoopAuth, SoopLive } from "./api";
import { SoopChatFunc, SoopClientOptions } from "./types";
import { SoopChannel } from "./api";
export declare class SoopClient {
    readonly options: SoopClientOptions;
    live: SoopLive;
    channel: SoopChannel;
    auth: SoopAuth;
    constructor(options?: SoopClientOptions);
    get chat(): SoopChatFunc;
    fetch(url: string, options?: RequestInit): Promise<Response>;
}
