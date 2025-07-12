from django.shortcuts import render
from django.db import models
from blog.models import Comment, Post, Tag


def get_related_posts_count(tag):
    return tag.posts.count()


def get_likes_count(post):
    return post.likes.count()


def serialize_post(post):
    return {
        'title': post.title,
        'teaser_text': post.text[:200],
        'author': post.author.username,
        'comments_amount': post.comment_set.count(),
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
        'first_tag_title': post.tags.first().title if post.tags.exists() else None,
        'likes_amount': post.likes.count(),
    }


def serialize_post_optimized(post):
    return {
        'title': post.title,
        'teaser_text': post.text[:200],
        'author': post.author.username,
        'comments_amount': post.comments_count,
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
        'first_tag_title': post.tags.all()[0].title if post.tags.all() else None,
        'likes_amount': post.likes_count,
    }


def serialize_tag(tag):
    return {
        'title': tag.title,
        'posts_with_tag': tag.posts.count(),
    }


def index(request):
    # 1. Получаем ID и количество лайков для популярных постов (только агрегация)
    popular_posts_data = Post.objects.annotate(
        likes_count=models.Count('likes')
    ).order_by('-likes_count').values('id', 'likes_count')[:5]

    # 2. Получаем ID постов для дальнейшей выборки
    post_ids = [item['id'] for item in popular_posts_data]
    
    # 3. Получаем количество комментариев для этих постов (отдельная агрегация)
    comments_data = Post.objects.filter(
        id__in=post_ids
    ).annotate(
        comments_count=models.Count('comments')
    ).values('id', 'comments_count')

    # 4. Создаем словари для быстрого доступа
    likes_mapping = {item['id']: item['likes_count'] for item in popular_posts_data}
    comments_mapping = {item['id']: item['comments_count'] for item in comments_data}

    # 5. Получаем полные объекты постов с префетчами
    posts = Post.objects.filter(
        id__in=post_ids
    ).prefetch_related(
        'tags',
        'author',
    )

    # 6. Добавляем вычисленные значения к каждому посту
    for post in posts:
        post.likes_count = likes_mapping[post.id]
        post.comments_count = comments_mapping.get(post.id, 0)

    # Сортируем по количеству лайков (как в исходном запросе)
    most_popular_posts = sorted(posts, key=lambda x: x.likes_count, reverse=True)

    # Аналогичная оптимизация для свежих постов
    fresh_posts_data = Post.objects.order_by('-published_at').values('id')[:5]
    fresh_post_ids = [item['id'] for item in fresh_posts_data]
    
    fresh_comments_data = Post.objects.filter(
        id__in=fresh_post_ids
    ).annotate(
        comments_count=models.Count('comments')
    ).values('id', 'comments_count')

    fresh_likes_data = Post.objects.filter(
        id__in=fresh_post_ids
    ).annotate(
        likes_count=models.Count('likes')
    ).values('id', 'likes_count')

    comments_mapping = {item['id']: item['comments_count'] for item in fresh_comments_data}
    likes_mapping = {item['id']: item['likes_count'] for item in fresh_likes_data}

    fresh_posts = Post.objects.filter(
        id__in=fresh_post_ids
    ).prefetch_related(
        'tags',
        'author',
    )

    for post in fresh_posts:
        post.comments_count = comments_mapping.get(post.id, 0)
        post.likes_count = likes_mapping.get(post.id, 0)

    popular_tags = Tag.objects.prefetch_related('posts').annotate(
        post_count=models.Count('posts')
    ).order_by('-post_count')[:5]

    context = {
        'most_popular_posts': [serialize_post_optimized(post) for post in most_popular_posts],
        'page_posts': [serialize_post_optimized(post) for post in fresh_posts],
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
    }
    return render(request, 'index.html', context)


def post_detail(request, slug):
    post = Post.objects.prefetch_related(
        'tags',
        'author',
        models.Prefetch('comment_set', queryset=Comment.objects.select_related('author')),
        'likes'
    ).get(slug=slug)

    serialized_comments = [{
        'text': comment.text,
        'published_at': comment.published_at,
        'author': comment.author.username,
    } for comment in post.comment_set.all()]

    serialized_post = {
        'title': post.title,
        'text': post.text,
        'author': post.author.username,
        'comments': serialized_comments,
        'likes_amount': post.likes.count(),
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
    }

    popular_tags = Tag.objects.prefetch_related('posts').annotate(
        post_count=models.Count('posts')
    ).order_by('-post_count')[:5]

    most_popular_posts = Post.objects.prefetch_related(
    'tags',
    'author',
).annotate(
    likes_count=models.Subquery(
        Post.objects.filter(
            id=models.OuterRef('id')
        ).annotate(
            cnt=models.Count('likes')
        ).values('cnt')[:1]
    ),
    comments_count=models.Subquery(
        Post.objects.filter(
            id=models.OuterRef('id')
        ).annotate(
            cnt=models.Count('comments')
        ).values('cnt')[:1]
    )
).order_by('-likes_count')[:5]

    context = {
        'post': serialized_post,
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
        'most_popular_posts': [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, 'post-details.html', context)


def tag_filter(request, tag_title):
    tag = Tag.objects.prefetch_related('posts').get(title=tag_title)

    related_posts = Post.objects.prefetch_related(
        'tags',
        'author',
        'likes',
        'comment_set'
    ).filter(tags=tag)[:20]

    popular_tags = Tag.objects.prefetch_related('posts').annotate(
        post_count=models.Count('posts')
    ).order_by('-post_count')[:5]

    most_popular_posts = Post.objects.prefetch_related(
        'tags',
        'author',
        'likes',
        'comment_set'
    ).annotate(
        likes_count=models.Count('likes', distinct=True)
    ).order_by('-likes_count')[:5]

    context = {
        'tag': tag.title,
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
        'posts': [serialize_post(post) for post in related_posts],
        'most_popular_posts': [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, 'posts-list.html', context)


def contacts(request):
    return render(request, 'contacts.html', {})