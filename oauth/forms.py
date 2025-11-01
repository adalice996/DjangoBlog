from django.contrib.auth.forms import forms
from django.forms import widgets


class RequireEmailForm(forms.Form):
    """
    OAuth认证中要求用户提供电子邮箱的表单
    
    用途：
    - 当用户通过第三方OAuth登录但未提供邮箱时
    - 要求用户手动输入邮箱地址以完成注册/绑定流程
    """
    
    # 邮箱字段：必填字段，用于接收用户输入的电子邮箱
    email = forms.EmailField(
        label='电子邮箱',  # 表单标签显示为中文
        required=True     # 必须填写
    )
    
    # OAuth用户ID字段：隐藏字段，用于传递OAuth用户的ID
    oauthid = forms.IntegerField(
        widget=forms.HiddenInput,  # 使用隐藏输入控件，不在页面上显示
        required=False              # 非必填字段
    )

    def __init__(self, *args, **kwargs):
        """
        初始化方法，用于自定义表单字段的显示属性
        """
        # 调用父类的初始化方法
        super(RequireEmailForm, self).__init__(*args, **kwargs)
        
        # 为邮箱字段添加HTML属性，改善用户体验
        self.fields['email'].widget = widgets.EmailInput(
            attrs={
                'placeholder': "email",        # 输入框内的提示文字
                "class": "form-control"       # Bootstrap样式类
            }
        )
