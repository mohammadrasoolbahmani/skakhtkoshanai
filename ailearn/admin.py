from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import CourseSettings, RegistrationRequest, Student, Attendance, SessionDayNote, StudentAchievement


@admin.register(CourseSettings)
class CourseSettingsAdmin(admin.ModelAdmin):
    list_display = ('course_title', 'fee_amount', 'sessions_count', 'card_number', 'card_holder')

    def has_add_permission(self, request):
        return not CourseSettings.objects.exists()


@admin.register(SessionDayNote)
class SessionDayNoteAdmin(admin.ModelAdmin):
    list_display = ('session_number', 'date_shamsi', 'topic_or_note', 'updated_at')
    search_fields = ('session_number', 'topic_or_note', 'date_shamsi')


@admin.register(StudentAchievement)
class StudentAchievementAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'session_number', 'title', 'file_name', 'file_size_str', 'uploaded_at_shamsi', 'download_link')
    list_filter = ('session_number', 'uploaded_at')
    search_fields = ('student__first_name', 'student__last_name', 'student__phone', 'title', 'file_name')

    def download_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" style="color:#2563EB; font-weight:bold;">دانلود فایل 📥</a>', obj.file.url)
        return "—"
    download_link.short_description = "دانلود"


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'age', 'education_level', 'fee_amount', 'receipt_thumbnail', 'status_badge', 'created_at_shamsi')
    list_filter = ('status', 'gender', 'education_level', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'tracking_code')
    readonly_fields = ('created_at', 'approved_at', 'rejected_at', 'receipt_large_view')
    actions = ['approve_selected_requests', 'reject_selected_requests']

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "نام و نام خانوادگی"

    def receipt_thumbnail(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;" /></a>', obj.receipt_image.url, obj.receipt_image.url)
        return "—"
    receipt_thumbnail.short_description = "تصویر رسید"

    def receipt_large_view(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px;" /></a>', obj.receipt_image.url, obj.receipt_image.url)
        return "تصویری بارگذاری نشده است"
    receipt_large_view.short_description = "نمای کامل رسید واریزی"

    def status_badge(self, obj):
        colors = {
            'pending': '#F59E0B',
            'approved': '#10B981',
            'rejected': '#EF4444',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html('<span style="color: white; background-color: {}; padding: 3px 10px; border-radius: 12px; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_badge.short_description = "وضعیت"

    @admin.action(description="تایید درخواست‌های انتخاب‌شده و فعال‌سازی حساب کاربری")
    def approve_selected_requests(self, request, queryset):
        count = 0
        for req in queryset.filter(status='pending'):
            req.status = 'approved'
            req.approved_at = timezone.now()
            req.save()

            student, created = Student.objects.get_or_create(
                phone=req.phone,
                defaults={
                    'first_name': req.first_name,
                    'last_name': req.last_name,
                    'password': req.requested_password,
                    'age': req.age,
                    'gender': req.gender,
                    'education_level': req.education_level,
                    'registration_request': req,
                    'receipt_image': req.receipt_image,
                    'tracking_code': req.tracking_code,
                    'fee_amount': req.fee_amount,
                    'is_active': True,
                    'approved_at': req.approved_at
                }
            )
            count += 1
        self.message_user(request, f"{count} درخواست با موفقیت تایید و حساب آن‌ها فعال گردید.")

    @admin.action(description="رد / لغو درخواست‌های انتخاب‌شده")
    def reject_selected_requests(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='rejected',
            rejected_at=timezone.now()
        )
        self.message_user(request, f"{count} درخواست لغو / رد شدند.")


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0


class StudentAchievementInline(admin.TabularInline):
    model = StudentAchievement
    extra = 0
    readonly_fields = ('uploaded_at', 'file_name', 'file_size_str')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'age', 'education_level', 'is_active', 'approved_at_shamsi', 'receipt_thumbnail')
    list_filter = ('is_active', 'gender', 'education_level', 'approved_at')
    search_fields = ('first_name', 'last_name', 'phone', 'tracking_code')
    inlines = [AttendanceInline, StudentAchievementInline]

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "نام و نام خانوادگی"

    def receipt_thumbnail(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 6px;" /></a>', obj.receipt_image.url, obj.receipt_image.url)
        return "—"
    receipt_thumbnail.short_description = "رسید تاییدشده"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session_number', 'status', 'note', 'updated_at')
    list_filter = ('session_number', 'status', 'updated_at')
    search_fields = ('student__first_name', 'student__last_name', 'student__phone', 'note')
