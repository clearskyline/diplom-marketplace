from rest_framework import throttling

class UserSignUpThrottle(throttling.AnonRateThrottle):
  scope = 'user_signup'
  # rate = '1/minute'
  def allow_request(self, request, view):
    # if request.method == "GET":
    #   return True
    return super().allow_request(request, view)
