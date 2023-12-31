from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .forms import NewsForm
from .models import CategorySubscribe, News, Category
from django.contrib.auth.models import User
from .filters import NewsFilter
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.cache import cache


@login_required
def upgrade_me(request):
    user = request.user
    authors = Group.objects.get(name='authors')
    if not request.user.groups.filter(name='authors').exists():
        authors.user_set.add(user)
    return redirect('/news')


# Тут смотрим новости – news
class NewsList(ListView, LoginRequiredMixin):
    # Указываем модель, объекты которой мы будем выводить
    model = News
    # сортируем через наоборот
    ordering = '-pub_date'
    # Имя шаблона для новостей — News
    template_name = 'news.html'
    # Имя списка, в котором будут лежать все объекты.
    # Его надо указать, чтобы обратиться к списку объектов в html-шаблоне.
    context_object_name = 'news'
    # ✅указали количество записей на странице (не более 10)
    paginate_by = 3

    # Метод get_context_data позволяет изменить набор данных, который будет передан в шаблон.
    def get_context_data(self, **kwargs):
        # С помощью super() мы обращаемся к родительским классам
        # и вызываем у них метод get_context_data с теми же аргументами,
        # что и были переданы нам.
        # В ответе мы должны получить словарь.
        context = super().get_context_data(**kwargs)
        # # ✅Добавляем в контекст объект фильтрации.
        # context['filterset'] = self.filterset
        # К словарю добавим текущую дату в ключ 'time_now'.
        context['time_now'] = datetime.utcnow()
        # ✅доп переменная анонс (announcement) статей (их правда пока нет, но они будут)
        context['announcement'] = None
        return context


# Тут смотрим конкретную новость/статью – one_news
class NewsDetail(DetailView):
    # модель для получения информации по отдельной новости
    model = News
    # используем новый шаблон — one_news.html
    template_name = 'one_news.html'
    # название объекта, в котором будет выбранная статья
    context_object_name = 'one_news'
    queryset = News.objects.all()

    # ⚠️ переопределяем метод получения объекта (кэшируем пока не изменили)
    def get_object(self, *args, **kwargs):
        # метод get забирает значение по ключу, если его нет, то забирает None
        obj = cache.get(f'news-{self.kwargs["pk"]}', None)
        # если объекта нет в кэше, то получаем его и записываем в кэш
        if not obj:
            obj = super().get_object(queryset=self.queryset)
            cache.set(f'news-{self.kwargs["pk"]}', obj)

        return obj


class SearchView(ListView):
    model = News
    # сортируем через наоборот
    ordering = '-pub_date'
    template_name = 'search.html'
    # Имя списка, в котором будут лежать все объекты.
    # Его надо указать, чтобы обратиться к списку объектов в html-шаблоне.
    context_object_name = 'news'

    # Метод get_context_data позволяет изменить набор данных, который будет передан в шаблон.
    def get_context_data(self, **kwargs):
        # С помощью super() мы обращаемся к родительским классам
        # и вызываем у них метод get_context_data с теми же аргументами,
        # что и были переданы нам.
        # В ответе мы должны получить словарь.
        context = super().get_context_data(**kwargs)
        # ✅Добавляем в контекст объект фильтрации.
        context['filterset'] = self.filterset
        return context

    # Переопределяем функцию получения списка новостей
    def get_queryset(self):
        # Получаем обычный запрос
        queryset = super().get_queryset()
        # Используем наш класс фильтрации.
        # self.request.GET содержит объект QueryDict, который мы рассматривали в этом юните ранее.
        # Сохраняем нашу фильтрацию в объекте класса, чтобы потом добавить в контекст и использовать в шаблоне.
        self.filterset = NewsFilter(self.request.GET, queryset)
        # Возвращаем из функции отфильтрованный список новостей
        return self.filterset.qs


# обновляем (редактируем) новость
class NewsUpdate(PermissionRequiredMixin, UpdateView):
    model = News
    form_class = NewsForm
    login_url = '/accounts/login/'
    template_name = 'post_edit.html'
    permission_required = ('NewsPaper.change_news',)


# создаем новость
class NewsCreate(PermissionRequiredMixin, CreateView):
    model = News
    fields = ['author', 'heading', 'text', 'pub_date', 'category']
    template_name = 'news_create.html'
    permission_required = ('NewsPaper.add_news',)
    # после создания возвращаемся на главную страницу
    success_url = reverse_lazy('news_list')

    # переопределяем метод form_valid и устанавливаем поле новости по умолчанию
    def form_valid(self, form):
        news = form.save(commit=False)
        news.news_type = 'NW'
        news.save()
        return super().form_valid(form)


# удаляем новость, после удаления на главную
class NewsDelete(DeleteView):
    model = News
    template_name = 'news_delete.html'
    success_url = reverse_lazy('news_list')


# создаем статью
class ArticleCreate(PermissionRequiredMixin, CreateView):
    model = News
    fields = ['author', 'heading', 'text', 'pub_date', 'category']
    template_name = 'article_create.html'
    permission_required = ('NewsPaper.add_news',)
    success_url = reverse_lazy('news_list')

    # переопределяем метод form_valid и устанавливаем поле статьи по умолчанию
    def form_valid(self, form):
        news = form.save(commit=False)
        news.type = 'AR'
        news.save()
        return super().form_valid(form)


# обновляем (редактируем) статью. После обновления на главную
class ArticleUpdate(PermissionRequiredMixin, UpdateView):
    model = News
    fields = ['author', 'heading', 'text']
    login_url = '/accounts/login/'
    template_name = 'article_edit.html'
    permission_required = ('NewsPaper.change_news',)
    # success_url = reverse_lazy('news_list')


# удаляем статью
class ArticleDelete(DeleteView):
    model = News
    template_name = 'news/article_delete.html'
    success_url = reverse_lazy('news_list')


# Список категорий:
class CategoryListView(NewsList):
    model = News
    template_name = 'news/category_list.html'
    context_object_name = 'category_news_list'

    def get_queryset(self):
        self.category = get_object_or_404(Category, id=self.kwargs['pk'])
        queryset = News.objects.filter(category=self.category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_not_subscriber'] = self.request.user not in self.category.subscribers.all()
        context['category'] = self.category
        return context


# Функция позволяющая подписаться на категорию
def subscribe_to_category(request, pk):
    current_user = request.user
    CategorySubscribe.objects.create(category=Category.objects.get(pk=pk), subscriber=User.objects.get(pk=current_user.id))

    return render(request, 'subscribe.html')


@login_required
def subscribe(request, pk):
    user = request.user
    category = Category.objects.get(id=pk)
    category.subscribers.add(user)

    message = 'Вы подписались на рассылку категории'
    return render(request, 'news/subscribe.html', {'category': category, 'message': message})
