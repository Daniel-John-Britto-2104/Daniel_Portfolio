from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact_submit, name="contact_submit"),
    path("hire/", views.contact_submit, name="hire_submit"),
    path("hire-me/", views.contact_submit, name="hire_me_submit"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
]