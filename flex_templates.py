from urllib.parse import quote

def create_toilet_flex_message(index, toilet_name, distance, address, encoded_name):
    """
    根據美編設計的樣式，動態產生「單一張」附近廁所資訊卡片
    """
    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F7F5EF",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": f"附近廁所 {index}",
                    "size": "sm",
                    "color": "#769382",
                    "weight": "bold",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": f"🚻 {toilet_name}",
                    "size": "xl",
                    "weight": "bold",
                    "color": "#4A4036",
                    "wrap": True,
                    "margin": "md",
                    "align": "center"
                },
                {
                    "type": "separator",
                    "margin": "lg",
                    "color": "#DDE5DF"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "lg",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📍",
                            "size": "md",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"距離約 {distance} 公尺",
                            "size": "md",
                            "weight": "bold",
                            "color": "#555555",
                            "margin": "sm",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🏠",
                            "size": "md",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": address,
                            "size": "md",
                            "weight": "bold",
                            "color": "#555555",
                            "margin": "sm",
                            "wrap": True
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F7F5EF",
            "paddingTop": "15px",
            "paddingBottom": "15px",
            "paddingStart": "15px",
            "paddingEnd": "15px",
            "spacing": "sm",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#C98F8F",
                            "height": "sm",
                            "flex": 1,
                            "action": {
                                "type": "postback",
                                "label": "💗 加入收藏",
                                "data": f"action=favorite&toilet_id={toilet_name}"
                            }
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#7895A8",
                            "height": "sm",
                            "flex": 1,
                            "action": {
                                "type": "uri",
                                "label": "🗺️ 查看地圖",
                                "uri": f"https://www.google.com/maps/search/?api=1&query={encoded_name}"
                            }
                        }
                    ]
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#C7A66A",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "⭐ 留下評價",
                        "uri": f"https://liff.line.me/2011608763-NWNQFgKI?toilet_id={encoded_name}"
                    }
                }
            ]
        }
    }


def create_favorites_flex(favorites_list):
    """
    根據美編設計，動態產生「我的收藏」列表卡片
    """
    count = len(favorites_list)
    contents = [
        {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#769382",
            "paddingAll": "20px",
            "cornerRadius": "xl",
            "contents": [
                {
                    "type": "text",
                    "text": "MY FAVORITES",
                    "color": "#FFFFFF",
                    "size": "xs",
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": "💗 我的收藏",
                    "color": "#FFFFFF",
                    "size": "xl",
                    "weight": "bold",
                    "margin": "sm"
                },
                {
                    "type": "text",
                    "text": "你收藏的廁所都在這裡",
                    "color": "#E8EFEA",
                    "size": "sm",
                    "margin": "sm"
                }
            ]
        },
        {
            "type": "box",
            "layout": "horizontal",
            "backgroundColor": "#FFFFFF",
            "paddingAll": "15px",
            "cornerRadius": "lg",
            "margin": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "目前收藏",
                    "color": "#888888",
                    "size": "sm",
                    "gravity": "center"
                },
                {
                    "type": "text",
                    "text": f"{count} 間",
                    "color": "#769382",
                    "size": "md",
                    "weight": "bold",
                    "align": "end",
                    "gravity": "center"
                }
            ]
        }
    ]

    for i, name in enumerate(favorites_list, start=1):
        encoded_name = quote(name)
        item_box = {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#FFFFFF",
            "cornerRadius": "lg",
            "margin": "md",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#769382",
                            "width": "4px",
                            "cornerRadius": "sm"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "paddingStart": "md",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"收藏 {i:02d}",
                                    "color": "#769382",
                                    "size": "xs",
                                    "weight": "bold"
                                },
                                {
                                    "type": "text",
                                    "text": name,
                                    "color": "#333333",
                                    "size": "md",
                                    "weight": "bold",
                                    "wrap": True,
                                    "margin": "sm"
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "md",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#769382",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "📍 查看地圖",
                                "uri": f"https://www.google.com/maps/search/?api=1&query={encoded_name}"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "移除",
                                "data": f"action=unfavorite&toilet_id={name}"
                            }
                        }
                    ]
                }
            ]
        }
        contents.append(item_box)

    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F7F5EF",
            "paddingAll": "15px",
            "contents": contents
        }
    }