from django.contrib import admin
from django.db.models import Count, Prefetch
from blog.models import Post, Tag, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'likes_count', 'comments_count')
    list_select_related = ('author',)
    raw_id_fields = ('likes', 'tags')
    search_fields = ('title', 'author__username')
    list_filter = ('published_at', 'tags')
    date_hierarchy = 'published_at'
    autocomplete_fields = ['tags']
    list_per_page = 50
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('tags', 'likes')
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'
    
    def comments_count(self, obj):
        return obj.comments.count()
    comments_count.short_description = 'Comments'
    
    def get_changelist_instance(self, request):
        changelist = super().get_changelist_instance(request)
        
        likes_counts = {
            p['id']: p['likes_count']
            for p in Post.objects.filter(
                id__in=[obj.id for obj in changelist.result_list]
            ).annotate(likes_count=Count('likes')).values('id', 'likes_count')
        }
        
        comments_counts = {
            p['id']: p['comments_count']
            for p in Post.objects.filter(
                id__in=[obj.id for obj in changelist.result_list]
            ).annotate(comments_count=Count('comments')).values('id', 'comments_count')
        }
        
        for obj in changelist.result_list:
            obj._cached_likes_count = likes_counts.get(obj.id, 0)
            obj._cached_comments_count = comments_counts.get(obj.id, 0)
            
        return changelist
    
    def likes_count(self, obj):
        return getattr(obj, '_cached_likes_count', obj.likes.count())
    likes_count.admin_order_field = '_cached_likes_count'
    
    def comments_count(self, obj):
        return getattr(obj, '_cached_comments_count', obj.comments.count())
    comments_count.admin_order_field = '_cached_comments_count'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('title', 'posts_count')
    search_fields = ('title',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            Prefetch('posts', queryset=Post.objects.only('id'))
        ).annotate(_posts_count=Count('posts', distinct=True))
    
    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Posts'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post_link', 'text_preview', 'published_at')
    list_select_related = ('author', 'post')
    raw_id_fields = ('post', 'author')
    search_fields = ('author__username', 'text', 'post__title')
    list_filter = ('published_at',)
    date_hierarchy = 'published_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'post', 'author'
        ).only(
            'text', 'published_at', 'author__username', 'post__title', 'post__id'
        )
    
    def post_link(self, obj):
        from django.utils.html import format_html
        return format_html('<a href="{}">{}</a>', 
                         f'/admin/blog/post/{obj.post.id}/',
                         obj.text[:50] + '...' if len(obj.text) > 50 else obj.text)
    post_link.short_description = 'Post preview'
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text preview'