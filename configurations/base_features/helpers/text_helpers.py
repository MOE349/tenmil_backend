def slugify(text):
    return text.lower().replace(" ", "_")


def snake_to_title(text):
    all_capitals = ['id']
    return ' '.join(word.capitalize() if word not in all_capitals else word.upper() for word in text.split('_'))
