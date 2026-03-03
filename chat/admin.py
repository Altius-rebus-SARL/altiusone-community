from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('id', 'sender', 'role', 'content', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_ai_conversation', 'created_at', 'updated_at')
    list_filter = ('is_ai_conversation',)
    search_fields = ('title',)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('content',)
