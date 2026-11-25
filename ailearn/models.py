from django.db import models
from django.utils import timezone
import jdatetime


def format_shamsi(dt, with_time=True):
    if not dt:
        return "—"
    try:
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        if with_time:
            return jdt.strftime("%Y/%m/%d - %H:%M")
        return jdt.strftime("%Y/%m/%d")
    except Exception:
        return str(dt)


class CourseSettings(models.Model):
    course_title = models.CharField(
        max_length=200, 
        default="دوره جامع هوش مصنوعی دبیرستان سخت‌کوشان", 
        verbose_name="عنوان دوره"
    )
    fee_amount = models.PositiveIntegerField(default=600000, verbose_name="هزینه دوره عادی (تومان)")
    family_fee_amount = models.PositiveIntegerField(default=300000, verbose_name="هزینه دوره خانواده (تومان)")
    sessions_count = models.PositiveIntegerField(default=12, verbose_name="تعداد کل جلسات")
    card_number = models.CharField(max_length=50, default="6219861987276812", verbose_name="شماره کارت مقصد")
    card_holder = models.CharField(max_length=150, default="محمد رسول بهمنی", verbose_name="نام صاحب حساب")

    class Meta:
        verbose_name = "تنظیمات دوره"
        verbose_name_plural = "تنظیمات دوره"

    def __str__(self):
        return f"{self.course_title} - {self.fee_amount:,} تومان (خانواده: {self.family_fee_amount:,} تومان)"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        if obj.card_number != "6219861987276812" or obj.card_holder != "محمد رسول بهمنی":
            obj.card_number = "6219861987276812"
            obj.card_holder = "محمد رسول بهمنی"
            obj.save()
        return obj


class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید منشی'),
        ('approved', 'تایید شده و حساب فعال'),
        ('rejected', 'لغو / رد شده'),
    ]

    GENDER_CHOICES = [
        ('male', 'آقا'),
        ('female', 'خانم'),
    ]

    REGISTRATION_TYPE_CHOICES = [
        ('regular', 'ثبت‌نام عادی (۶۰۰ هزار تومان)'),
        ('family', 'ثبت‌نام خانواده / والدین، خواهر و برادر (۳۰۰ هزار تومان)'),
    ]

    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    phone = models.CharField(max_length=20, db_index=True, verbose_name="شماره همراه (نام کاربری)")
    age = models.PositiveIntegerField(verbose_name="سن")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="جنسیت")
    education_level = models.CharField(max_length=80, verbose_name="مقطع تحصیلی")
    requested_password = models.CharField(max_length=128, verbose_name="رمز عبور انتخابی")
    registration_type = models.CharField(
        max_length=20, 
        choices=REGISTRATION_TYPE_CHOICES, 
        default='regular', 
        verbose_name="نوع ثبت‌نام"
    )
    fee_amount = models.PositiveIntegerField(default=600000, verbose_name="مبلغ پرداختی (تومان)")
    tracking_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد رهگیری / ارجاع")
    receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', verbose_name="تصویر فیش / رسید واریزی")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="وضعیت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت درخواست")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ تایید")
    rejected_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ رد")
    admin_notes = models.TextField(blank=True, null=True, verbose_name="یادداشت منشی")

    class Meta:
        verbose_name = "درخواست ثبت‌نام و رسید"
        verbose_name_plural = "درخواست‌های ثبت‌نام و رسیدها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone}) - {self.get_status_display()}"

    @property
    def created_at_shamsi(self):
        return format_shamsi(self.created_at)

    @property
    def approved_at_shamsi(self):
        return format_shamsi(self.approved_at)


class Student(models.Model):
    GENDER_CHOICES = [
        ('male', 'آقا'),
        ('female', 'خانم'),
    ]

    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    phone = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="شماره همراه (نام کاربری)")
    password = models.CharField(max_length=128, verbose_name="رمز عبور")
    age = models.PositiveIntegerField(verbose_name="سن")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="جنسیت")
    education_level = models.CharField(max_length=80, verbose_name="مقطع تحصیلی")
    registration_type = models.CharField(max_length=20, default='regular', verbose_name="نوع ثبت‌نام")
    registration_request = models.OneToOneField(
        RegistrationRequest, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='student_profile',
        verbose_name="درخواست اولیه مرتبط"
    )
    receipt_image = models.ImageField(upload_to='approved_receipts/%Y/%m/', blank=True, null=True, verbose_name="رسید تاییدشده")
    tracking_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد رهگیری")
    fee_amount = models.PositiveIntegerField(default=600000, verbose_name="مبلغ پرداختی (تومان)")
    is_active = models.BooleanField(default=True, verbose_name="حساب فعال است")
    approved_at = models.DateTimeField(default=timezone.now, verbose_name="تاریخ تایید و فعال‌سازی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "دانش‌آموز تاییدشده"
        verbose_name_plural = "دانش‌آموزان تاییدشده"
        ordering = ['-approved_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"

    @property
    def approved_at_shamsi(self):
        return format_shamsi(self.approved_at)


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances', verbose_name="دانش‌آموز")
    session_number = models.PositiveIntegerField(verbose_name="شماره جلسه")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name="وضعیت")
    note = models.CharField(max_length=255, blank=True, null=True, verbose_name="یادداشت روز کاری / جلسه")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        verbose_name = "حضور و غیاب"
        verbose_name_plural = "سوابق حضور و غیاب"
        unique_together = ('student', 'session_number')
        ordering = ['student', 'session_number']

    def __str__(self):
        return f"{self.student} - جلسه {self.session_number}: {self.get_status_display()}"


class SessionDayNote(models.Model):
    session_number = models.PositiveIntegerField(unique=True, verbose_name="شماره جلسه")
    date_shamsi = models.CharField(max_length=50, blank=True, null=True, verbose_name="تاریخ شمسی جلسه")
    topic_or_note = models.TextField(blank=True, null=True, verbose_name="یادداشت و مبحث این روز کاری")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        verbose_name = "یادداشت روز کاری جلسات"
        verbose_name_plural = "یادداشت‌های روزهای کاری جلسات"
        ordering = ['session_number']

    def __str__(self):
        return f"جلسه {self.session_number} ({self.date_shamsi or 'بدون تاریخ'})"


class StudentAchievement(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='achievements', verbose_name="دانش‌آموز")
    session_number = models.PositiveIntegerField(verbose_name="شماره جلسه مرتبط")
    title = models.CharField(max_length=200, verbose_name="عنوان دستاورد / ساخته")
    file = models.FileField(upload_to='achievements/%Y/%m/', verbose_name="فایل دستاورد")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_size_str = models.CharField(max_length=50, blank=True, null=True, verbose_name="حجم فایل")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    student_notes = models.TextField(blank=True, null=True, verbose_name="توضیحات فراگیر")

    class Meta:
        verbose_name = "دستاورد و پروژه کلاسی دانش‌آموز"
        verbose_name_plural = "دستاوردها و پروژه‌های کلاسی"
        ordering = ['session_number', '-uploaded_at']

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} - جلسه {self.session_number}: {self.title}"

    @property
    def uploaded_at_shamsi(self):
        return format_shamsi(self.uploaded_at)
