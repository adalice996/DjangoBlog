# 由 Django 4.1.7 在 2023-03-02 07:14 自动生成
# 这是一个数据库迁移文件，用于创建或修改数据库结构

# 导入必要的模块和类
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    """数据库迁移类，继承自Django的Migration基类"""

    # 标记这是初始迁移（项目中的第一个迁移文件）
    initial = True

    # 定义本迁移所依赖的其他迁移
    # 这里依赖于auth应用的迁移，因为我们要扩展用户模型
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    # 定义要执行的数据操作
    operations = [
        # 创建新表的操作
        migrations.CreateModel(
            # 自定义用户模型名称
            name='BlogUser',
            # 定义模型的字段
            fields=[
                # ID字段：自增主键，BigAutoField支持更大的数字范围
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                
                # 密码字段：存储加密后的密码，最大长度128字符
                ('password', models.CharField(max_length=128, verbose_name='password')),
                
                # 最后登录时间：记录用户最后一次登录的时间，可以为空
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                
                # 超级用户标志：标记用户是否拥有所有权限
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                
                # 用户名字段：必须唯一，有长度限制和字符验证
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                
                # 名字字段：可选字段
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                
                # 姓氏字段：可选字段
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                
                # 邮箱字段：可选字段
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                
                # 员工状态：标记用户是否可以登录管理后台
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                
                # 活跃状态：标记用户账户是否激活（软删除机制）
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                
                # 加入日期：用户注册时间，默认为当前时间
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                
                # ========== 以下是自定义字段 ==========
                
                # 昵称字段：用户的显示名称，可选字段，最大长度100
                ('nickname', models.CharField(blank=True, max_length=100, verbose_name='昵称')),
                
                # 创建时间：记录创建时间，默认为当前时间
                ('created_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                
                # 最后修改时间：记录最后修改时间，默认为当前时间
                ('last_mod_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='修改时间')),
                
                # 创建来源：记录用户账户的创建来源（如：网站注册、管理员创建等）
                ('source', models.CharField(blank=True, max_length=100, verbose_name='创建来源')),
                
                # ========== 以下是Django权限系统相关的多对多字段 ==========
                
                # 用户组：多对多关系，用户所属的权限组
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                
                # 用户权限：多对多关系，用户拥有的具体权限
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            # 模型的元数据配置
            options={
                'verbose_name': '用户',           # 在管理后台显示的单数名称
                'verbose_name_plural': '用户',    # 在管理后台显示的复数名称
                'ordering': ['-id'],              # 默认按ID倒序排列（最新的在前面）
                'get_latest_by': 'id',            # 指定获取最新记录的字段
            },
            # 指定模型的管理器
            managers=[
                # 使用Django原生的UserManager来管理用户对象
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
