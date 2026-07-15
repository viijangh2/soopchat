"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SoopChannel = void 0;
const const_1 = require("../const");
class SoopChannel {
    client;
    constructor(client) {
        this.client = client;
    }
    async station(streamerId, baseUrl = const_1.DEFAULT_BASE_URLS.soopChannelBaseUrl) {
        return this.client.fetch(`${baseUrl}/api/${streamerId}/station`, {
            method: "GET",
        })
            .then(response => response.json())
            .then(data => {
            return {
                profile_image: data["profile_image"],
                station: data["station"],
                broad: data["broad"],
                starballoon_top: data["starballoon_top"],
                sticker_top: data["sticker_top"],
                subscription: data["subscription"],
                is_best_bj: data["is_best_bj"],
                is_partner_bj: data["is_partner_bj"],
                is_ppv_bj: data["is_ppv_bj"],
                is_af_supporters_bj: data["is_af_supporters_bj"],
                is_shopfreeca_bj: data["is_shopfreeca_bj"],
                is_favorite: data["is_favorite"],
                is_subscription: data["is_subscription"],
                is_owner: data["is_owner"],
                is_manager: data["is_manager"],
                is_notice: data["is_notice"],
                is_adsence: data["is_adsence"],
                is_mobile_push: data["is_mobile_push"],
                subscribe_visible: data["subscribe_visible"],
                country: data["country"],
                current_timestamp: data["current_timestamp"]
            };
        });
    }
}
exports.SoopChannel = SoopChannel;
