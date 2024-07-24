from rest_framework.authentication import TokenAuthentication


class XAuthTokenAuthentication(TokenAuthentication):
    keyword = "X-Auth-Token"
