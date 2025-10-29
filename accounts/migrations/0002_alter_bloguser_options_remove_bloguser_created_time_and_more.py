# 由 Django 4.2.5 在 2023-09-06 13:13 自动生成
# 这是一个后续的迁移文件，用于修改之前创建的模型结构

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    """数据库迁移类，用于修改已有的BlogUser模型"""

    # 定义本迁移所依赖的迁移文件
    # 这里依赖于accounts应用中的第一个初始迁移
    dependencies = [
        ('accounts', '0001_initial'),  # 必须等待初始迁移完成才能执行本迁移
    ]

    # 定义要执行的数据操作序列
    operations = [
        # 操作1：修改模型的元选项（Meta options）
        migrations.AlterModelOptions(
            name='bloguser',  # 指定要修改的模型名称
            options={
                'get_latest_by': 'id',      # 指定按id字段获取最新记录
                'ordering': ['-id'],        # 默认按id倒序排列（新的在前）
                'verbose_name': 'user',     # 修改单数名称为英文'user'
                'verbose_name_plural': 'user',  # 修改复数名称为英文'user'
            },
        ),
        
        # 操作2：移除created_time字段
        # 这个字段在0001_initial迁移中被创建，现在需要删除
        migrations.RemoveField(
            model_name='bloguser',  # 从BlogUser模型中
            name='created_time',    # 移除created_time字段
        ),
        
        # 操作3：移除last_mod_time字段
        migrations.RemoveField(
            model_name='bloguser',   # 从BlogUser模型中
            name='last_mod_time',    # 移除last_mod_time字段
        ),
        
        # 操作4：添加新的creation_time字段
        migrations.AddField(
            model_name='bloguser',  # 向BlogUser模型添加字段
            name='creation_time',   # 新字段名
            # 字段类型和配置：日期时间字段，默认值为当前时间
            field=models.DateTimeField(
                default=django.utils.timezone.now,  # 默认使用当前时间
                verbose_name='creation time'        # 在管理后台显示为'creation time'
            ),
        ),
        
        # 操作5：添加新的last_modify_time字段
        migrations.AddField(
            model_name='bloguser',  # 向BlogUser模型添加字段
            name='last_modify_time',  # 新字段名
            # 字段类型和配置：日期时间字段，默认值为当前时间
            field=models.DateTimeField(
                default=django.utils.timezone.now,  # 默认使用当前时间
                verbose_name='last modify time'     # 在管理后台显示为'last modify time'
            ),
        ),
        
        # 操作6：修改nickname字段的显示名称
        migrations.AlterField(
            model_name='bloguser',  # 指定要修改的模型
            name='nickname',        # 指定要修改的字段名
            # 新的字段配置：保持类型和约束不变，只修改显示名称
            field=models.CharField(
                blank=True,           # 允许为空（可选字段）
                max_length=100,       # 最大长度100字符
                verbose_name='nick name'  # 修改显示名称为英文'nick name'
            ),
        ),
        
        # 操作7：修改source字段的显示名称
        migrations.AlterField(
            model_name='bloguser',  # 指定要修改的模型
            name='source',          # 指定要修改的字段名
            # 新的字段配置：保持类型和约束不变，只修改显示名称
            field=models.CharField(
                blank=True,              # 允许为空（可选字段）
                max_length=100,          # 最大长度100字符
                verbose_name='create source'  # 修改显示名称为英文'create source'
            ),
        ),
    ]
