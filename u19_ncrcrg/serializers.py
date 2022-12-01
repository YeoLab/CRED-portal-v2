import io

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.parsers import JSONParser


def deserializer(json):
    stream = io.BytesIO(json)
    data = JSONParser().parse(stream)

    return data


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
