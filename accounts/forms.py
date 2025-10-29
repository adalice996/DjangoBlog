# 导入Django表单模块
from django import forms
# 导入获取用户模型的方法和密码验证工具
from django.contrib.auth import get_user_model, password_validation
# 导入Django内置的认证表单和用户创建表单
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
# 导入验证错误异常
from django.core.exceptions import ValidationError
# 导入表单控件
from django.forms import widgets
# 导入国际化翻译函数
from django.utils.translation import gettext_lazy as _
# 导入自定义工具模块
from . import utils
# 导入自定义用户模型
from .models import BlogUser


class LoginForm(AuthenticationForm):
    """
    用户登录表单
    继承自Django内置的AuthenticationForm，添加自定义样式
    """
    
    def __init__(self, *args, **kwargs):
        """
        初始化方法，设置表单字段的控件属性
        """
        # 调用父类的初始化方法
        super(LoginForm, self).__init__(*args, **kwargs)
        
        # 为用户名字段设置文本输入控件，添加占位符和CSS类
        self.fields['username'].widget = widgets.TextInput(
            attrs={
                'placeholder': "username",  # 输入框内的提示文字
                "class": "form-control"     # Bootstrap样式类
            })
        
        # 为密码字段设置密码输入控件，添加占位符和CSS类
        self.fields['password'].widget = widgets.PasswordInput(
            attrs={
                'placeholder': "password",  # 输入框内的提示文字
                "class": "form-control"     # Bootstrap样式类
            })


class RegisterForm(UserCreationForm):
    """
    用户注册表单
    继承自Django内置的UserCreationForm，添加邮箱字段和自定义样式
    """
    
    def __init__(self, *args, **kwargs):
        """
        初始化方法，设置表单字段的控件属性
        """
        super(RegisterForm, self).__init__(*args, **kwargs)
        
        # 为各个字段设置相应的输入控件，添加占位符和CSS类
        self.fields['username'].widget = widgets.TextInput(
            attrs={'placeholder': "username", "class": "form-control"})
        self.fields['email'].widget = widgets.EmailInput(
            attrs={'placeholder': "email", "class": "form-control"})
        self.fields['password1'].widget = widgets.PasswordInput(
            attrs={'placeholder': "password", "class": "form-control"})
        self.fields['password2'].widget = widgets.PasswordInput(
            attrs={'placeholder': "repeat password", "class": "form-control"})

    def clean_email(self):
        """
        邮箱验证方法
        检查邮箱是否已经被注册
        """
        # 获取清洗后的邮箱数据
        email = self.cleaned_data['email']
        
        # 检查数据库中是否已存在该邮箱
        if get_user_model().objects.filter(email=email).exists():
            # 如果邮箱已存在，抛出验证错误
            raise ValidationError(_("email already exists"))
        
        # 返回验证通过的邮箱
        return email

    class Meta:
        """
        表单的元数据配置
        """
        # 指定表单对应的用户模型
        model = get_user_model()
        # 指定在表单中显示的字段：用户名和邮箱
        fields = ("username", "email")


class ForgetPasswordForm(forms.Form):
    """
    忘记密码表单
    用于用户通过邮箱验证码重置密码
    """
    
    # 新密码字段1
    new_password1 = forms.CharField(
        label=_("New password"),  # 字段标签
        widget=forms.PasswordInput(  # 密码输入控件
            attrs={
                "class": "form-control",      # Bootstrap样式
                'placeholder': _("New password")  # 占位符文字
            }
        ),
    )

    # 新密码字段2（确认密码）
    new_password2 = forms.CharField(
        label="确认密码",  # 中文标签
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                'placeholder': _("Confirm password")  # 国际化占位符
            }
        ),
    )

    # 邮箱字段
    email = forms.EmailField(
        label='邮箱',  # 中文标签
        widget=forms.TextInput(  # 使用文本输入控件而不是EmailInput，可能是为了样式统一
            attrs={
                'class': 'form-control',
                'placeholder': _("Email")
            }
        ),
    )

    # 验证码字段
    code = forms.CharField(
        label=_('Code'),  # 验证码标签
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _("Code")
            }
        ),
    )

    def clean_new_password2(self):
        """
        确认密码验证方法
        检查两次输入的新密码是否一致，并验证密码强度
        """
        # 从数据中获取两个密码字段的值
        password1 = self.data.get("new_password1")
        password2 = self.data.get("new_password2")
        
        # 检查两次输入的密码是否一致
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("passwords do not match"))
        
        # 使用Django内置的密码验证器验证密码强度
        password_validation.validate_password(password2)

        # 返回验证通过的密码
        return password2

    def clean_email(self):
        """
        邮箱验证方法
        检查邮箱是否在系统中注册过
        """
        user_email = self.cleaned_data.get("email")
        
        # 检查邮箱是否存在于用户数据库中
        if not BlogUser.objects.filter(email=user_email).exists():
            # TODO: 这里的报错提示会暴露邮箱是否注册，如果不想暴露可以修改提示信息
            raise ValidationError(_("email does not exist"))
        
        return user_email

    def clean_code(self):
        """
        验证码验证方法
        使用工具函数验证邮箱和验证码的匹配关系
        """
        code = self.cleaned_data.get("code")
        
        # 调用工具模块的verify函数验证验证码
        error = utils.verify(
            email=self.cleaned_data.get("email"),
            code=code,
        )
        
        # 如果验证返回错误信息，抛出验证错误
        if error:
            raise ValidationError(error)
        
        return code


class ForgetPasswordCodeForm(forms.Form):
    """
    获取忘记密码验证码的表单
    用于用户输入邮箱获取密码重置验证码
    """
    
    email = forms.EmailField(
        label=_('Email'),  # 邮箱字段，支持国际化标签
        # 注意：这个表单类没有完整定义，可能需要添加widget等配置
    )
