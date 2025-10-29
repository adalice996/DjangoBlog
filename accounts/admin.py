# 导入Django表单相关模块
from django import forms
# 导入Django内置的用户管理类
from django.contrib.auth.admin import UserAdmin
# 导入Django内置的用户修改表单
from django.contrib.auth.forms import UserChangeForm
# 导入用户名字段类
from django.contrib.auth.forms import UsernameField
# 导入国际化翻译函数
from django.utils.translation import gettext_lazy as _

# 注册模型到管理后台的注释提示
# Register your models here.

# 导入自定义的用户模型
from .models import BlogUser


class BlogUserCreationForm(forms.ModelForm):
    """
    自定义用户创建表单
    用于在Django管理后台创建新用户
    """
    
    # 密码输入字段1：用于输入密码
    password1 = forms.CharField(
        label=_('password'),  # 字段标签，支持国际化
        widget=forms.PasswordInput  # 使用密码输入控件（显示为星号）
    )
    
    # 密码输入字段2：用于确认密码
    password2 = forms.CharField(
        label=_('Enter password again'),  # 字段标签：再次输入密码
        widget=forms.PasswordInput  # 使用密码输入控件
    )

    class Meta:
        # 指定该表单对应的模型
        model = BlogUser
        # 指定在表单中显示的字段，这里只显示邮箱
        fields = ('email',)

    def clean_password2(self):
        """
        密码验证方法
        检查两次输入的密码是否一致
        """
        # 从清洗后的数据中获取两个密码字段的值
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        # 验证逻辑：如果两个密码都存在且不匹配，抛出验证错误
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("passwords do not match"))
        
        # 返回确认密码的值
        return password2

    def save(self, commit=True):
        """
        保存用户的方法
        重写以处理密码加密和设置用户来源
        """
        # 调用父类的save方法，但不立即提交到数据库（commit=False）
        user = super().save(commit=False)
        
        # 使用Django的密码加密方法设置密码
        user.set_password(self.cleaned_data["password1"])
        
        # 如果commit为True，则保存到数据库
        if commit:
            # 设置用户来源为管理后台
            user.source = 'adminsite'
            user.save()
        
        # 返回用户对象
        return user


class BlogUserChangeForm(UserChangeForm):
    """
    自定义用户信息修改表单
    用于在Django管理后台编辑现有用户信息
    继承自Django内置的UserChangeForm
    """

    class Meta:
        # 指定该表单对应的模型
        model = BlogUser
        # 显示所有字段
        fields = '__all__'
        # 指定字段类型映射，确保用户名字段使用正确的字段类
        field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        """
        初始化方法
        可以在这里添加自定义的初始化逻辑
        """
        # 调用父类的初始化方法
        super().__init__(*args, **kwargs)


class BlogUserAdmin(UserAdmin):
    """
    自定义用户管理类
    配置Django管理后台中用户模型的显示和行为
    继承自Django内置的UserAdmin
    """
    
    # 指定用户编辑时使用的表单
    form = BlogUserChangeForm
    # 指定创建新用户时使用的表单
    add_form = BlogUserCreationForm
    
    # 配置列表页面显示的字段
    list_display = (
        'id',           # 用户ID
        'nickname',     # 昵称
        'username',     # 用户名
        'email',        # 邮箱
        'last_login',   # 最后登录时间
        'date_joined',  # 注册时间
        'source'        # 用户来源
    )
    
    # 配置列表中哪些字段可以作为链接点击进入编辑页面
    list_display_links = ('id', 'username')
    
    # 配置默认排序规则：按ID倒序排列（最新的在前面）
    ordering = ('-id',)
    
    # 配置搜索功能支持的字段
    search_fields = ('username', 'nickname', 'email')
