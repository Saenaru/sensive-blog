from django.shortcuts import render, get_object_or_404
from django.db import models
from blog.models import Comment, Post, Tag

def serialize_tag(tag):
    return {
        'title': tag.title,
        'posts_with_tag': tag.posts_count,
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

def get_common_context():
    """Возвращает общие данные для нескольких страниц"""
    most_popular_posts = Post.objects.popular().with_tags_and_author().fetch_with_comments_count()[:5]
    popular_tags = Tag.objects.popular()[:5]
    
    return {
        'most_popular_posts': [serialize_post_optimized(post) for post in most_popular_posts],
        'popular_tags': [serialize_tag(tag) for tag in popular_tags],
    }

def index(request):
    fresh_posts = (
        Post.objects
        .order_by('-published_at')
        .with_tags_and_author()
        .annotate(likes_count=models.Count('likes'))
        .fetch_with_comments_count()[:5]
    )
    
    context = get_common_context()
    context.update({
        'page_posts': [serialize_post_optimized(post) for post in fresh_posts],
    })
    
    return render(request, 'index.html', context)

def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects
        .with_tags_and_author()
        .prefetch_related(
            models.Prefetch('comments', queryset=Comment.objects.select_related('author')),
            'likes'
        )
        .annotate(likes_count=models.Count('likes')),
        slug=slug
    )
    
    post.comments_count = Comment.objects.filter(post=post).count()

    similar_posts = (
        Post.objects
        .similar(post)
        .with_tags_and_author()
        .annotate(likes_count=models.Count('likes'))
        .fetch_with_comments_count()
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

    context = get_common_context()
    context.update({
        'post': serialized_post,
    })
    
    return render(request, 'post-details.html', context)

def tag_filter(request, tag_title):
    tag = get_object_or_404(Tag.objects.with_posts_count(), title=tag_title)
    
    related_posts = (
        Post.objects
        .filter(tags=tag)
        .with_tags_and_author()
        .annotate(likes_count=models.Count('likes'))
        .fetch_with_comments_count()[:20]
    )

    context = get_common_context()
    context.update({
        'tag': tag.title,
        'posts': [serialize_post_optimized(post) for post in related_posts],
    })
    
    return render(request, 'posts-list.html', context)

def contacts(request):
    context = get_common_context()
    return render(request, 'contacts.html', context)