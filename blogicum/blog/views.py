from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View
)

from .forms import CommentForm, PostForm, ProfileEditForm
from .models import Category, Comment, Post


User = get_user_model()
MAX_QUANTITY_POST = 10


def get_post_data(self):
    return get_object_or_404(
        self.model.objects.select_related(
            'location', 'author', 'category'
        ).filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        ), pk=self.kwargs['id']
    )


class PostMixin:
    model = Post
    template_name = 'blog/create.html'


class CommentMixin(LoginRequiredMixin, View):
    model = Comment
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def get_object(self):
        return get_object_or_404(
            Comment,
            pk=self.kwargs['comment_id'],
        )

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            return redirect('blog:post_detail', id=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("blog:post_detail",
                       kwargs={'id': self.kwargs['post_id']})


class CommonListMixin(ListView):
    model = Post
    paginate_by = MAX_QUANTITY_POST

    def get_queryset(self):
        queryset_select = (
            self.model.objects.select_related(
                'location', 'author', 'category'
            ).filter(
                is_published=True,
                category__is_published=True,
                pub_date__lte=timezone.now()
            )
        )
        queryset_filter = queryset_select.annotate(
            comment_count=Count("comments")
        ).order_by("-pub_date")
        return queryset_filter


class PostVerifyMixin(LoginRequiredMixin):
    form_class = PostForm
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)


class IndexListView(CommonListMixin):
    template_name = 'blog/index.html'


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        if self.request.user.is_authenticated:
            return get_object_or_404(
                self.model.objects.select_related(
                    'location', 'author', 'category'
                ).filter(
                    Q(author=self.request.user)
                    | (
                        Q(pub_date__lte=timezone.now())
                        & Q(is_published=True)
                        & Q(category__is_published=True)
                    ), pk=self.kwargs['id']
                )
            )
        return get_post_data(self)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class CategoryPostsListView(CommonListMixin):
    template_name = 'blog/category.html'

    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )
        return (super().get_queryset().select_related('category')
                .filter(category=self.category))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostCreateView(LoginRequiredMixin, PostMixin, CreateView):
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:profile", args=[self.request.user])


class PostUpdateView(PostVerifyMixin, PostMixin, UpdateView):
    pass


class PostDeleteView(PostVerifyMixin, PostMixin, DeleteView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PostForm(instance=self.object)
        return context

    def get_success_url(self):
        return reverse("blog:profile", kwargs={"username": self.request.user})


class ProfileListView(CommonListMixin):
    template_name = 'blog/profile.html'

    def get_queryset(self):
        self.user = get_object_or_404(
            User,
            username=self.kwargs['username']
        )

        if (self.request.user == self.user):

            return (
                self.model.objects.select_related('author')
                .filter(author__username=self.user.username)
                .annotate(comment_count=Count("comments"))
                .order_by("-pub_date")
            )
        queryset = super().get_queryset()
        return queryset.select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'blog/user.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse("blog:profile", args=[self.request.user])


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    post_obj = None

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(
            Post, id=self.kwargs.get('post_id')
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:post_detail",
                       kwargs={'id': self.kwargs['post_id']})


class CommentUpdateView(CommentMixin, UpdateView):
    form_class = CommentForm


class CommentDeleteView(CommentMixin, DeleteView):
    pass
