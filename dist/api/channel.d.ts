import { SoopClient } from "../client";
interface StationInfo {
    profile_image: string;
    station: Station;
    broad: Broad;
    starballoon_top: StarBalloonTop[];
    sticker_top: StickerTop[];
    subscription: Subscription;
    is_best_bj: boolean;
    is_partner_bj: boolean;
    is_ppv_bj: boolean;
    is_af_supporters_bj: boolean;
    is_shopfreeca_bj: boolean;
    is_favorite: boolean;
    is_subscription: boolean;
    is_owner: boolean;
    is_manager: boolean;
    is_notice: boolean;
    is_adsence: boolean;
    is_mobile_push: boolean;
    subscribe_visible: string;
    country: string;
    current_timestamp: string;
}
interface Station {
    display: Display;
    groups: Group[];
    menus: Menu[];
    upd: Upd;
    vods: Vod[];
    broad_start: string;
    grade: number;
    jointime: string;
    station_name: string;
    station_no: number;
    station_title: string;
    total_broad_time: number;
    user_id: string;
    user_nick: string;
    active_no: number;
}
interface Display {
    main_type: string;
    title_type: string;
    title_text: string;
    profile_text: string;
    skin_type: number;
    skin_no: number;
    title_skin_image: string;
}
interface Group {
    idx: number;
    group_no: number;
    priority: number;
    info: {
        group_name: string;
        group_class_name: string;
        group_background_color: string;
    };
}
interface Menu {
    bbs_no: number;
    station_no: number;
    auth_no: number;
    w_auth_no: number;
    display_type: number;
    rnum: number;
    line: number;
    indention: number;
    name: string;
    name_font: number;
    main_view_yn: number;
    view_type: number;
}
interface Upd {
    station_no: number;
    user_id: string;
    asp_code: number;
    fan_cnt: number;
    today0_visit_cnt: number;
    today1_visit_cnt: number;
    total_visit_cnt: number;
    today0_ok_cnt: number;
    today1_ok_cnt: number;
    today0_fav_cnt: number;
    today1_fav_cnt: number;
    total_ok_cnt: number;
    total_view_cnt: number;
}
interface Vod {
    bbs_no: number;
    station_no: number;
    auth_no: number;
    w_auth_no: number;
    display_type: number;
    rnum: number;
    line: number;
    indention: number;
    name: string;
    name_font: number;
    main_view_yn: number;
    view_type: number;
}
interface Broad {
    user_id: string;
    broad_no: number;
    broad_title: string;
    current_sum_viewer: number;
    broad_grade: number;
    is_password: boolean;
}
interface StarBalloonTop {
    user_id: string;
    user_nick: string;
    profile_image: string;
}
interface StickerTop {
    user_id: string;
    user_nick: string;
    profile_image: string;
}
interface Subscription {
    total: number;
    tier1: number;
    tier2: number;
}
export declare class SoopChannel {
    private client;
    constructor(client: SoopClient);
    station(streamerId: string, baseUrl?: string): Promise<StationInfo>;
}
export {};
