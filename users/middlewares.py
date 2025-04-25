



class JWTAuthenticationMiddleware():
    def process_request(self, request):
        data = request.data
        if 'refresh_token' in data:
            token = data.get('refresh_token')
        else:
            token = request.META.get('HTTP_AUTHORIZATION', None)
        if token:
            pass

    @staticmethod
    def get_jwt_user(request):
        # user_jwt = get_user(request)
        # if user_jwt.is_authenticated():
        #     return user_jwt
        # token = request.META.get('HTTP_AUTHORIZATION', None)

        # user_jwt = AnonymousUser()
        # if token is not None:
        #     try:
        #         user_jwt = jwt.decode(
        #             token,
        #             settings.WP_JWT_TOKEN,
        #         )
        #         user_jwt = User.objects.get(
        #             id=user_jwt['data']['user']['id']
        #         )
        #     except Exception as e: # NoQA
        #         traceback.print_exc()
        # return user_jwt
        return