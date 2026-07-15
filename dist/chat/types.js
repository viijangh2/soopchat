"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatType = exports.ChatDelimiter = void 0;
var ChatDelimiter;
(function (ChatDelimiter) {
    ChatDelimiter["STARTER"] = "\u001B\t";
    ChatDelimiter["SEPARATOR"] = "\f";
    ChatDelimiter["ELEMENT_START"] = "\u0011";
    ChatDelimiter["ELEMENT_END"] = "\u0012";
    ChatDelimiter["SPACE"] = "\u0006";
})(ChatDelimiter || (exports.ChatDelimiter = ChatDelimiter = {}));
var ChatType;
(function (ChatType) {
    ChatType["PING"] = "0000";
    ChatType["CONNECT"] = "0001";
    ChatType["ENTER_CHAT_ROOM"] = "0002";
    ChatType["EXIT"] = "0004";
    ChatType["CHAT"] = "0005";
    ChatType["DISCONNECT"] = "0007";
    ChatType["ENTER_INFO"] = "0012";
    ChatType["TEXT_DONATION"] = "0018";
    ChatType["AD_BALLOON_DONATION"] = "0087";
    ChatType["SUBSCRIBE"] = "0093";
    ChatType["NOTIFICATION"] = "0104";
    ChatType["EMOTICON"] = "0109";
    ChatType["VIDEO_DONATION"] = "0105";
    ChatType["VIEWER"] = "0127";
    // UNKNOWN = "0009",
    // UNKNOWN = "0054",
    // UNKNOWN = "0088",
    // UNKNOWN = "0094",
})(ChatType || (exports.ChatType = ChatType = {}));
