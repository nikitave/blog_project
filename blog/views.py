import random
import datetime
import os
from fuzzysearch import find_near_matches

from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.utils import timezone
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import authenticate, login, logout
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Count

from .models import *
from .forms import *


def get_groups(article_set):
    """
    Sorts latest articles by number of comments and group them by 2 and 3
    Returned list format: [[mode, articles], [mode, articles], ...]
    mode is mode to display articles in browser
    """

    if len(article_set) == 0:
        return []
    elif len(article_set) == 1:
        return [[0, list(article_set)]]
    elif len(article_set) > 30:
        articles = article_set.order_by('-pub_date')[random.randint(10, 30)]
        articles.annotate(num_comments=Count('comment')).order_by('-num_comments')
    else:
        articles = article_set.annotate(num_comments=Count('comment')).order_by('-num_comments')

    # group articles
    groups = []
    while len(articles) > 1:
        if len(articles) == 4:
            slice, articles = articles[2:], articles[:2]
            groups.append([random.randint(1, 3), slice])
        if len(articles) == 3:
            groups.append([4, articles])
            break
        elif len(articles) == 2:
            groups.append([random.randint(1, 3), articles])
            break

        mode = random.randint(1, 4)
        if mode <= 3:
            slice, articles = articles[len(articles)-2:], articles[:len(articles)-2]
            groups.append([mode, slice])
        else:
            slice, articles = articles[len(articles)-3:], articles[:len(articles)-3]
            groups.append([mode, slice])
    return groups


def search_in(sequence, q):
    if not type(sequence) is list:
        try:
            sequence = list(sequence)
        except TypeError as TR:
            raise TR

    l_dist = len(q) // 4

    result = []
    for i in range(len(sequence)):
        if find_near_matches(q, sequence[i].name, max_l_dist=l_dist) != []:
            result.append(sequence[i])
    if len(result) == 0:
        return None

    return result


def render_empty_form(request, form, template, message=''):
    context = {
        'message': message,
        'form': form,
    }
    return render(request, template, context)

# done
def index(request):
    template = 'blog/blog_index.html'

    if request.user.is_authenticated and not Writer.objects.filter(name=request.user.username).exists():
        logout(request)

    articles = Article.objects.order_by('-pub_date')
    if len(articles) > 1:
        article1 = articles[0]
        articles = Article.objects.exclude(name=article1.name, author=article1.author)
        groups = get_groups(articles)
    elif len(articles) == 1:
        article1, articles = articles[0], []
        groups = []
    else:
        article1 = None
        groups = []

    context = {
        'article1': article1,
        'groups': groups,
    }
    return render(request, template, context)

# done
def article(request, writer_name, article_name):
    template = 'blog/article.html'

    writer = get_object_or_404(Writer, name=writer_name)
    article = get_object_or_404(Article, name=article_name)

    article_set = writer.article_set.exclude(name=article.name)
    if article_set.exists():
        recommended_article = article_set.order_by('-pub_date')[0]
    else:
        recommended_article = None

    form = CommentForm()
    context = {
        'article': article,
        'form': form,
        'recommended_article': recommended_article,
        'comments': article.comment_set.order_by('-comment_date'),
        'message': None,
    }
    if not request.user.is_authenticated:
        context['message'] = 'You cannot comment. Please login'

    if request.method == 'GET':
        return render(request, template, context)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            context['message'] = 'You must login to comment'
            return render(request, template, context)

        form = CommentForm(request.POST)

        if form.is_valid():

            author = get_object_or_404(Writer, name=request.user.username)
            text = form.cleaned_data['text']
            comment_date = timezone.now()

            article.comment_set.create(
                author = author,
                text = text,
                comment_date = comment_date,
            )
            return HttpResponseRedirect(reverse('blog:article', args=(writer_name, article_name)))
        else:
            context['message'] = 'Form is invalid'
            return render(request, template, context)

# done
def writer(request, writer_name):
    template = 'blog/writer.html'

    writer = get_object_or_404(Writer, name=writer_name)

    articles = writer.article_set.order_by('-pub_date')
    if articles == []:
        message = 'No articles'
    else:
        message = ''
    authenticated = request.user.is_authenticated

    context = {
        'message': message,
        'writer': writer,
        'articles': articles,
    }
    return render(request, template, context)

# done
def my_page(request):
    template = 'blog/my_page.html'

    if not request.user.is_authenticated:
        return HttpResponse('<h1>401 unauthorized</h1>', status=401)

    writer = get_object_or_404(Writer, name=request.user.username)

    articles = writer.article_set.order_by('-pub_date')
    if articles == []:
        message = 'No articles'
    else:
        message = ''

    add_form = AddForm()
    image_form = WriterImageForm()
    bio_form = WriterBioForm(initial={'age': writer.age, 'bio': writer.bio})

    context = {
        'tags': Tag.objects.all(),
        'message': message,
        'writer': writer,
        'articles': articles,
        'image_form': image_form,
        'bio_form': bio_form,
        'add_form': add_form,
    }

    if request.method == 'GET':
        return render(request, template, context)

    elif request.method == 'POST':

        if 'bio_form' in request.POST:

            bio_form = WriterBioForm(request.POST)
            if bio_form.is_valid:

                age = request.POST['age']
                bio = request.POST['bio']

                if age == '':
                    age = None
                if bio == '':
                    bio = None

                writer.age = age
                writer.bio = bio
                writer.save()

                return HttpResponseRedirect(reverse('blog:my_page'))
            else:
                context['message'] = 'Form is invalid'
                return render(request, template, context)

        elif 'add_form' in request.POST:

            # add article form

            add_form = AddForm(request.POST, request.FILES)
            if add_form.is_valid():
                tag_name = request.POST['tag']

                text = add_form.cleaned_data['text']
                name = add_form.cleaned_data['name']
                spec_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
                for char in spec_chars:
                    if char in name:
                        context['message'] = 'Name cannot contain special characters: '
                        for i in range(len(spec_chars)):
                            context['message'] += str(spec_chars[i])
                        add_form = AddForm(initial={'text': text})
                        context['add_form'] = add_form
                        return render(request, template, context)

                if len(name) >= 100:
                    context['message'] = 'Name is too long'
                    context['add_form'] = AddForm(initial={'name': name, 'text': text})
                    return render(request, template, context)
                if len(text) >= 100000:
                    context['message'] = 'Text is too long'
                    context['add_form'] = AddForm(initial={'name': name, 'text': text})
                    return render(request, template, context)


                tag = get_object_or_404(Tag, name=tag_name)
                writer = Writer.objects.get(name=request.user.username)

                if list(writer.article_set.filter(name=name)) == []:

                    article = writer.article_set.create(
                        name = name,
                        text = text,
                        tag = tag,
                        pub_date = timezone.now(),
                        last_edit = timezone.now(),
                    )
                    article.upload_image(request.FILES['image'])

                    return HttpResponseRedirect(reverse('blog:my_page'))
                else:
                    context['message'] = 'This name is not available'
                    return render(request, template, context)
            else:
                context['message'] = 'Form is invalid'
                return render(request, template, context)

        elif 'image_form' in request.POST:

            # writer image form

            image_form = WriterImageForm(request.POST, request.FILES)
            if image_form.is_valid:
                writer.delete_image()
                writer.upload_image(request.FILES['image'])
                return HttpResponseRedirect(reverse('blog:my_page'))
            else:
                context['message'] = 'Form is invalid'
                return render(request, template, context)

# done
def my_article(request, article_name):
    template = 'blog/my_article.html'

    if not request.user.is_authenticated:
        return HttpResponse('<h1>401 unauthorized</h1>', status=401)

    writer = get_object_or_404(Writer, name=request.user.username)
    article = writer.article_set.get(name=article_name)
    context = {
        'article': article,
        'comments': article.comment_set.order_by('-comment_date'),
    }

    return render(request, template, context)

# done
def edit(request, article_name):
    template = 'blog/edit.html'

    user = request.user
    if not user.is_authenticated:
        return HttpResponse('<h1>401 unauthorized</h1>', status=401)

    writer = get_object_or_404(Writer, name=user.username)
    article = get_object_or_404(Article, name=article_name, author=writer)

    form = EditForm(initial={
        'name': article.name,
        'text': article.text,
        'tag': article.tag,
    })

    context = {
        'tags': Tag.objects.all(),
        'article': article,
        'message': '',
        'form': form,
    }

    if request.method == 'GET':
        return render(request, template, context)

    elif request.method == 'POST':
        form = EditForm(request.POST, request.FILES)
        if form.is_valid():
            tag_name = request.POST['tag']
            text = form.cleaned_data['text']

            name = form.cleaned_data['name']
            spec_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
            for char in spec_chars:
                if char in name:
                    context['message'] = 'Name cannot contain special characters: '
                    for i in range(len(spec_chars)):
                        context['message'] += str(spec_chars[i])
                    form = EditForm(initial={'text': text})
                    context['form'] = form
                    return render(request, template, context)

            if len(name) >= 100:
                context['message'] = 'Name is too long'
                context['form'] = EditForm(initial={'name': name, 'text': text})
                return render(request, template, context)
            if len(text) >= 100000:
                context['message'] = 'Text is too long'
                context['form'] = EditForm(initial={'name': name, 'text': text})
                return render(request, template, context)

            tag = get_object_or_404(Tag, name=tag_name)

            old_name = article.name
            article.name = name
            article.text = text
            article.tag = tag
            article.last_edit=timezone.now()

            if name != old_name and not 'image' in request.FILES:
                if article.image:
                    old = article.image.path
                else:
                    old = None

                dirname = os.path.join(settings.MEDIA_ROOT, 'articles/images')
                new = os.path.join(dirname, article.author.name + '_' + article.name + os.path.splitext(article.image.path)[1])

                os.rename(old, new)
                article.image = new

            article.save()

            if 'image' in request.FILES:
                image = request.FILES['image']
                article.upload_image(image)

            return HttpResponseRedirect(reverse('blog:my_article', args=(article.name, )))
        else:
            context['message'] = 'Form is invalid'
            return render(request, template, context)

# done
def delete(request, article_name):

    user = request.user
    if not user.is_authenticated:
        return HttpResponse('<h1>401 unauthorized</h1>', status=401)

    writer = Writer.objects.get(name=user.username)
    writer.article_set.get(name=article_name).delete_image()
    writer.article_set.get(name=article_name).delete()

    return HttpResponseRedirect(reverse('blog:my_page'))

# done
def log_in(request):
    template = 'blog/login.html'
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('blog:index'))

    form = LogInForm()
    context = {
        'form': form,
        'message': '',
    }

    if request.method == 'GET':
        return render(request, template, context)

    elif request.method == 'POST':
        form = LogInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse('blog:index'))
            else:
                if list(User.objects.filter(username=username)) == []:
                    context['message'] = 'User does not exist'
                    return render(request, template, context)
                else:
                    context['message'] = 'Wrong password'
                    return render(request, template, context)
        else:
            context['message'] = 'Form is invalid'

# done
def sign_up(request):
    template = 'blog/sign_up.html'

    form = SignUpForm()
    context = {
        'form': form,
        'message': ''
    }

    if request.method == 'GET':
        return render(request, template, context)

    elif request.method == 'POST':
        if request.user.is_authenticated:
            logout(request)

        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            if list(User.objects.filter(username=username)) == []:
                User.objects.create_user(username=username, password=password)
                writer = Writer.objects.create(name=username, age=0)

                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)

                return HttpResponseRedirect(reverse('blog:my_page'))
            else:
                context['message'] = "This name is occupied"
                return render(request, template, context)

        else:
            context['message'] = 'Form is invalid'
            return render(request, template, context)

# done
def log_out(request):
    if request.user.is_authenticated:
        logout(request)

    return HttpResponseRedirect(reverse('blog:index'))

# done
def authors(request):
    template = 'blog/authors.html'

    writers = Writer.objects.annotate(num_articles=Count('article')).order_by('-num_articles')
    context = {
        'writers': writers,
    }

    return render(request, template, context)

# done
def tags(request):
    template = 'blog/tags.html'

    tags = list(Tag.objects.annotate(num_articles=Count('article')).order_by('-num_articles'))

    if len(tags) == 0:
        tags, top_tags = None, None
    elif 1 <= len(tags) <= 3:
        top_tags, tags = tags, None
    else:
        top_tags, tags = tags[:3], tags[3:]

    context = {
        'tags': tags,
        'top_tags': top_tags
    }

    return render(request, template, context)

# done
def tag(request, tag_name):
    template = 'blog/tag.html'

    tag = Tag.objects.get(name=tag_name)
    articles = tag.article_set.order_by('-pub_date')

    context = {
        'tag': tag,
        'articles': articles,
    }

    return render(request, template, context)


def search(request):
    template = 'blog/search.html'

    q = request.GET.get('q')
    if len(q) == 0:
        return HttpResponseRedirect(reverse('blog:index'))

    articles = search_in(Article.objects.all(), q)
    writers = search_in(Writer.objects.all(), q)
    tags = search_in(Tag.objects.all(), q)

    context = {
        'articles': articles,
        'writers': writers,
        'tags': tags
    }

    return render(request, template, context)
