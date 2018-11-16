参数配置
==========

LOGGING
------------------------------------------------------------------------
默认值：`{}`

log配置

::

    {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'require_debug_false': {
                '()': 'tornadoapi.core.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'tornadoapi.core.log.RequireDebugTrue',
            },
        },
        'formatters': {
            'default': {
                'format': '%(asctime)s %(filename)s(%(lineno)d) %(levelname)s %(process)d %(message)s',
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'filters': ['require_debug_true'],
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'tornadoapi.core.log.AdminEmailHandler'
            },
            'tornadoapi.handler': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            }
        },
        'loggers': {
            'tornado.access': {
                'handlers': ['console'],
                'level': 'INFO',
            },
            'tornado.application': {
                'handlers': ['console'],
                'level': 'INFO',
            },
            'tornado.general': {
                'handlers': ['console'],
                'level': 'INFO',
            },
            'tornadoapi': {
                'handlers': ['console', 'mail_admins'],
                'level': 'INFO',
            },
            'tornadoapi.handler': {
                'handlers': ['tornadoapi.handler'],
                'level': 'INFO',
                'propagate': False,
            },
        }
    }

RESPONSE_CODE_TAG
------------------------------------------------------------------------
默认值：`'code'`

ApiHandler 返回值 code 对应 key

::

    RESPONSE_CODE_TAG = 'err_code'
    # ApiHandler 返回内容为
    {
        "err_code": "错误码",
        "message": "错误描述",
        "data": "数据"
    }

RESPONSE_MESSAGE_TAG
------------------------------------------------------------------------
默认值：`'message'`

ApiHandler 返回值 message 对应 key

::

    RESPONSE_MESSAGE_TAG = 'err_msg'
    # ApiHandler 返回内容为
    {
        "code": "错误码",
        "err_msg": "错误描述",
        "data": "数据"
    }

TEMPLATE_CONFIG
------------------------------------------------------------------------
默认值：`{'cache_directory': '_template_cache'}`

Jinja2 模板配置

::

    {
        'cache_directory': '_template_cache',  # 模版编译文件目录
        'autoescape': False,
        'cache_size', 50,
        'filesystem_checks', True,
        'block_start_string', defaults.BLOCK_START_STRING,
        'block_end_string', defaults.BLOCK_END_STRING,
        'variable_start_string', defaults.VARIABLE_START_STRING,
        'variable_end_string', defaults.VARIABLE_END_STRING,
        'comment_start_string', defaults.COMMENT_START_STRING,
        'comment_end_string', defaults.COMMENT_END_STRING,
        'line_statement_prefix', defaults.LINE_STATEMENT_PREFIX,
        'line_comment_prefix', defaults.LINE_COMMENT_PREFIX,
        'trim_blocks', defaults.TRIM_BLOCKS,
        'lstrip_blocks', defaults.LSTRIP_BLOCKS,
        'newline_sequence', defaults.NEWLINE_SEQUENCE,
        'keep_trailing_newline', defaults.KEEP_TRAILING_NEWLINE,
        'extensions', (),
        'optimized', True,
        'undefined', Undefined,
        'finalize', None
    }


ADMINS
------------------------------------------------------------------------
默认值：`[]`

系统管理员邮箱列表，通过 `tornadoapi.core.mail.mail_admins` 发送邮件的收件人

::

    [('John', 'john@example.com'), ('Mary', 'mary@example.com')]

MANAGERS
------------------------------------------------------------------------
默认值：`[]`

业务管理员邮箱列表，通过 `tornadoapi.core.mail.mail_managers` 发送邮件的收件人

::

    [('John', 'john@example.com'), ('Mary', 'mary@example.com')]

EMAIL_SUBJECT_PREFIX
------------------------------------------------------------------------
默认值：`'[Tornado Api]'`

邮件主题前缀，通过 `tornadoapi.core.mail.mail_admins` 和 `tornadoapi.core.mail.mail_managers` 发送邮件时主题前缀

DEFAULT_FROM_EMAIL
------------------------------------------------------------------------
默认值：`'webmaster@localhost'`

邮件发信人，`tornadoapi.core.mail.send_mail` 函数的默认发件人

SERVER_EMAIL
------------------------------------------------------------------------
默认值：`'root@localhost'`

错误邮件发信人，该地址只用于错误邮件， 不包括直接调用 `tornadoapi.core.mail.send_mail`

EMAIL_HOST
------------------------------------------------------------------------
默认值：`'localhost'`

邮件服务器

EMAIL_PORT
------------------------------------------------------------------------
默认值：`25`

邮件服务器端口

EMAIL_HOST_USER
------------------------------------------------------------------------
默认值：`''`

SMTP 身份验证用户名，如果为空，不会尝试进行身份验证

EMAIL_HOST_PASSWORD
------------------------------------------------------------------------
默认值：`''`

SMTP 身份验证密码
