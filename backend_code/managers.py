from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email_login, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email_login:
            raise ValueError('Email required')
        email_login = self.normalize_email(email_login)
        user = self.model(email_login=email_login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email_login, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email_login, password, **extra_fields)

    def create_superuser(self, email_login, password, **extra_fields):
        extra_fields.setdefault('area_code', 1)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email_login, password, **extra_fields)
