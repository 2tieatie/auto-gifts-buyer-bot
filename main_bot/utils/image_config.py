IMAGE_URLS = {
    "ru": {
        "welcome": "",
        "main_menu": "https://i.ibb.co/Fqzpyh29/Untitled-design-2.png",
        "settings": "",
        "language": "",
        "stars_menu": "https://i.ibb.co/bR79VjwB/Untitled-design-7.png",
        "premium_menu": "https://i.ibb.co/kVSS1SqG/Untitled-design-8.png",
        "profile": "",
        "autobuy": "https://i.ibb.co/d0J662Nx/Untitled-design-9.png",
        "stars_input": "",
        "error": "",
    },
    "en": {
        "welcome": "",
        "main_menu": "https://i.ibb.co/pCm8mGW/Untitled-design-1.png",
        "settings": "",
        "language": "",
        "stars_menu": "https://i.ibb.co/bR79VjwB/Untitled-design-7.png",
        "premium_menu": "https://i.ibb.co/kVSS1SqG/Untitled-design-8.png",
        "profile": "",
        "autobuy": "https://i.ibb.co/d0J662Nx/Untitled-design-9.png",
        "stars_input": "",
        "error": "",
    },
}


def get_image_url(lang: str, image_type: str) -> str:
    return IMAGE_URLS.get(lang, {}).get(
        image_type, IMAGE_URLS["en"].get(image_type, "")
    )
