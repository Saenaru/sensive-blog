from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class PostQuerySet(models.QuerySet):
    def popular(self):
        """Возвращает посты, отсортированные по количеству лайков"""
        return self.annotate(
            likes_count=models.Count('likes', distinct=True)
        ).order_by('-likes_count')
    
    def with_comments_and_likes_count(self):
        """Возвращает посты с аннотированными количествами комментариев и лайков"""
        return self.annotate(
            comments_count=models.Count('comments', distinct=True),
            likes_count=models.Count('likes', distinct=True)
        )

    def fetch_with_comments_count(self):
        """
        Оптимизированная замена annotate(Count('comments')) 
        Возвращает список постов с предзагруженным количеством комментариев
        
        Преимущества перед annotate:
        1. Не создает сложных SQL-запросов с подзапросами
        2. Работает быстрее для небольших наборов данных (5-20 постов)
        3. Позволяет использовать prefetch_related для комментариев
        """
        posts = list(self)
        if not posts:
            return posts
            
        from django.db.models import Count
        comments_counts = (
            Post.objects.filter(id__in=[post.id for post in posts])
            .annotate(comments_count=Count('comments'))
            .values('id', 'comments_count')
        )
        
        comments_mapping = {
            item['id']: item['comments_count'] 
            for item in comments_counts
        }
        
        for post in posts:
            post.comments_count = comments_mapping.get(post.id, 0)
            
        return posts
    
    def similar(self, post, limit=5):
        """
        Возвращает посты с общими тегами (похожие посты)
        Оптимизированная версия с одним запросом к БД
        """
        from django.db.models import Count
        
        tag_ids = post.tags.values_list('id', flat=True)
        
        return (
            self.exclude(id=post.id)
            .filter(tags__in=tag_ids)
            .annotate(common_tags=Count('tags'))
            .order_by('-common_tags', '-published_at')
            .distinct()[:limit]
        )

class TagQuerySet(models.QuerySet):
    def popular(self):
        return self.annotate(
            post_count=models.Count('posts')
        ).order_by('-post_count')

class Post(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст')
    slug = models.SlugField('Название в виде url', max_length=200)
    image = models.ImageField('Картинка')
    published_at = models.DateTimeField('Дата и время публикации')

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        limit_choices_to={'is_staff': True})
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        verbose_name='Кто лайкнул',
        blank=True)
    tags = models.ManyToManyField(
        'Tag',
        related_name='posts',
        verbose_name='Теги')

    objects = PostQuerySet.as_manager()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'пост'
        verbose_name_plural = 'посты'


class Tag(models.Model):
    title = models.CharField('Тег', max_length=20, unique=True)

    objects = TagQuerySet.as_manager()

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    def get_absolute_url(self):
        return reverse('tag_filter', args={'tag_title': self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = 'тег'
        verbose_name_plural = 'теги'


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост, к которому написан'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор')

    text = models.TextField('Текст комментария')
    published_at = models.DateTimeField('Дата и время публикации')

    def __str__(self):
        return f'{self.author.username} under {self.post.title}'

    class Meta:
        ordering = ['published_at']
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'

