from PIL import Image, ImageDraw
from app.analyzers.image.visible_marks import corner_sparkles


def test_corner_shape_is_an_unverified_clue():
    image = Image.new('RGB', (700, 1500), 'black')
    draw = ImageDraw.Draw(image)
    draw.polygon([(645,1410),(652,1427),(670,1435),(652,1442),(645,1460),(637,1442),(620,1435),(637,1427)], fill='gray')
    boxes = corner_sparkles(image)
    assert boxes and boxes[0][0] > .8 and boxes[0][1] > .8


def test_blank_circle_and_square_do_not_match():
    for shape in ('blank', 'circle', 'square'):
        image = Image.new('RGB', (700, 1500), 'black')
        draw = ImageDraw.Draw(image)
        if shape == 'circle':draw.ellipse((620,1410,670,1460), fill='white')
        if shape == 'square':draw.rectangle((620,1410,670,1460), fill='white')
        assert corner_sparkles(image) == []
