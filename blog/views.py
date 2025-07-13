from django.shortcuts import render
from django.db import models
from blog.models import Comment, Post, Tag


def serialize_tag(tag):
    return {
        'title': tag.title,
        'posts_with_tag': tag.posts_count if hasattr(tag, 'posts_count') else tag.posts.count(),
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


def index(request):
    # Оптимизация запросов для популярных постов
    most_popular_posts = (
        Post.objects
        .popular()
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts')))
        )[:5]
        .fetch_with_comments_count()
    )
    
    # Оптимизация запросов для свежих постов
    fresh_posts = (
        Post.objects
        .annotate(likes_count=models.Count('likes'))
        .order_by('-published_at')
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts')))
        )[:5]
        .fetch_with_comments_count()
    )
    
    # Оптимизация запросов для популярных тегов
    popular_tags = (
        Tag.objects
        .popular()
        .annotate(posts_count=models.Count('posts'))
        [:5]
    )
    
    context = {
        'most_popular_posts': [serialize_post_optimized(post) for post in most_popular_posts],
        'page_posts': [serialize_post_optimized(post) for post in fresh_posts],
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
    }
    return render(request, 'index.html', context)


# Остальные функции остаются без изменений
def post_detail(request, slug):
    post = Post.objects.prefetch_related(
        models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts'))),
        'author',
        models.Prefetch('comments', queryset=Comment.objects.select_related('author')),
        'likes'
    ).annotate(likes_count=models.Count('likes')).get(slug=slug)

    similar_posts = (
        Post.objects
        .similar(post)
        .annotate(likes_count=models.Count('likes'))
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts'))))
        .fetch_with_comments_count()
    )

    most_popular_posts = (
        Post.objects
        .popular()
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts'))))
        [:5]
        .fetch_with_comments_count()
    )

    popular_tags = (
        Tag.objects
        .popular()
        .annotate(posts_count=models.Count('posts'))
        [:5]
    )

    serialized_comments = [{
        'text': comment.text,
        'published_at': comment.published_at,
        'author': comment.author.username,
    } for comment in post.comments.all()]

    serialized_post = {
        'title': post.title,
        'text': post.text,
        'author': post.author.username,
        'comments': serialized_comments,
        'likes_amount': post.likes_count,
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
        'similar_posts': [serialize_post_optimized(p) for p in similar_posts],
    }

    context = {
        'post': serialized_post,
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
        'most_popular_posts': [serialize_post_optimized(post) for post in most_popular_posts],
    }
    
    return render(request, 'post-details.html', context)


def tag_filter(request, tag_title):
    tag = Tag.objects.annotate(posts_count=models.Count('posts')).get(title=tag_title)
    
    related_posts = (
        Post.objects
        .filter(tags=tag)
        .annotate(likes_count=models.Count('likes'))  # Добавляем аннотацию для лайков
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts')))
        )[:20]
        .fetch_with_comments_count()
    )

    popular_tags = (
        Tag.objects
        .popular()
        .annotate(posts_count=models.Count('posts'))
        [:5]
    )

    most_popular_posts = (
        Post.objects
        .popular()  # Метод popular() уже включает аннотацию likes_count
        .prefetch_related(
            'author',
            models.Prefetch('tags', queryset=Tag.objects.annotate(posts_count=models.Count('posts')))
        )[:5]
        .fetch_with_comments_count()
    )

    context = {
        'tag': tag.title,
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
        'posts': [serialize_post_optimized(post) for post in related_posts],  # Используем optimized версию
        'most_popular_posts': [serialize_post_optimized(post) for post in most_popular_posts],
    }
    return render(request, 'posts-list.html', context)


def contacts(request):
    return render(request, 'contacts.html', {})