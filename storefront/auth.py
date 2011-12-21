import re

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from storefront.models import Account
from storefront.lib import encoder

class ApiUrlBackend(ModelBackend):
    def authenticate(self, username=None, password=None, request=None):
        password = password.rstrip('/')
        if username == 'apiurl@indextank.com':
            code = re.search(r'.*@([^\.]+)\.api\..*', password)
            if code:
                code = code.group(1)
                account_id = encoder.from_key(code)
                account = Account.objects.get(id=account_id)
                if account.get_private_apiurl() == password:
                    return account.user.user
                else:
                    return None
            else:
                return None
        return None
