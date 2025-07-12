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
        'comments_amount': post.comments.count(),
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
        'likes_amount': getattr(post, 'likes_count', post.likes.count()),
    }


def serialize_tag(tag):
    return {
        'title': tag.title,
        'posts_with_tag': tag.posts.count(),
    }


def index(request):
    most_popular_posts = (
        Post.objects
        .popular()
        .prefetch_related('author', 'tags')[:5]
        .fetch_with_comments_count()
    )
    
    fresh_posts = (
        Post.objects
        .order_by('-published_at')
        .prefetch_related('author', 'tags')[:5]
        .fetch_with_comments_count()
    )
    
    popular_tags = Tag.objects.popular()[:5]
    
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
        models.Prefetch('comments', queryset=Comment.objects.select_related('author')),
        'likes'
    ).get(slug=slug)

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
        'likes_amount': post.likes.count(),
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
    }

    popular_tags = Tag.objects.popular()[:5]

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
        'comments'
    ).filter(tags=tag)[:20]

    popular_tags = Tag.objects.popular()[:5]

    most_popular_posts = Post.objects.prefetch_related(
        'tags',
        'author',
        'likes',
        'comments'
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