import os
from PIL import Image

from django.core.files.storage import default_storage
from django.db.models import *
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation


def resize_image(path, square=False):
    image = Image.open(path)
    image.thumbnail((1500, 1500))

    if square:
        width_to_cut = abs(image.width - image.height) // 2
        if image.width > image.height:
            upper, lower = 0, image.height
            left, right = width_to_cut, image.width - width_to_cut
        elif image.height > image.width:
            left, right = 0, image.width
            upper, lower = width_to_cut, image.height - width_to_cut
        else:
            left, upper, right, lower = 0, 0, image.width, image.height

        image = image.crop((left, upper, right, lower))
    image.save(path)

    return Image.open(path)


def upload(instanse, path, file, square=False):
    os.chdir(settings.MEDIA_ROOT)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'wb+') as dest:
        for c in file.chunks():
            dest.write(c)
    resize_image(path, square)
    instanse.image = path

    instanse.save()
    return path


def delete(instanse):
    if instanse.image:
        try:
            path = instanse.image.path
            if path != os.path.join(settings.MEDIA_ROOT, r'writers\images\default.jpg') and path != os.path.join(settings.MEDIA_ROOT, r'tags/images/black.jpg'):
                default_storage.delete(path)
        except SuspiciousFileOperation:
            path = None
        instanse.image = None
        instanse.save()
    else:
        path = None
    return path


class Article(Model):
    author = ForeignKey('Writer', on_delete=CASCADE)
    name = CharField(max_length=70)
    text = CharField(max_length=100000)
    image = ImageField(max_length=1000, upload_to=r'articles/images', null=True)
    tag = ForeignKey('Tag', on_delete=CASCADE, null=True)
    pub_date = DateTimeField()
    last_edit = DateTimeField()


    def __str__(self):
        return self.name


    def upload_image(self, file):
        # delete old
        self.delete_image()

        # get filename
        name = self.author.name + '_' + self.name + os.path.splitext(os.path.basename(file.name))[1]
        filename = os.path.join(r'articles/images', name)

        # upload
        return upload(self, filename, file)


    def delete_image(self):
        delete(self)


class Writer(Model):
    name = CharField(max_length=50)
    bio = CharField(max_length=1000, null=True)
    age = IntegerField(null=True)
    image = ImageField(max_length=1000, upload_to=r'writers/images', default=r'writers/images/default.jpg', null=True)


    def __str__(self):
        return self.name


    def upload_image(self, file):
        # delete old
        self.delete_image()

        # get filename
        name = self.name + '_image' + os.path.splitext(os.path.basename(file.name))[1]
        filename = os.path.join(r'writers/images', name)

        # upload
        return upload(self, filename, file, square=True)


    def delete_image(self):
        delete(self)


class Comment(Model):
    article = ForeignKey('Article', on_delete=CASCADE)
    author = ForeignKey('Writer', on_delete=CASCADE)
    text = CharField(max_length=1000)
    comment_date = DateTimeField()


    def __str__(self):
        return self.text


class Tag(Model):
    name = CharField(max_length=70)
    image = ImageField(max_length=1000, upload_to=r'tags/images', default=r'tags/images/black.jpg', null=True)


    def __str__(self):
        return self.name
