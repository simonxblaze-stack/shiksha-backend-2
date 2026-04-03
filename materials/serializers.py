from rest_framework import serializers
from .models import StudyMaterial, MaterialFile


class MaterialFileSerializer(serializers.ModelSerializer):

    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()  # ✅ added

    class Meta:
        model = MaterialFile
        fields = ["id", "file_url", "file_name", "file_size"]

    def get_file_name(self, obj):
        return obj.filename()

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_file_size(self, obj):
        if obj.file:
            return round(obj.file.size / (1024 * 1024), 2)  # MB
        return 0


class StudyMaterialSerializer(serializers.ModelSerializer):

    files = serializers.SerializerMethodField()

    # ✅ FIXED NAME (important)
    chapter_name = serializers.SerializerMethodField()

    # ✅ NEW FIELD
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = StudyMaterial
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "chapter_name",
            "subject_name",
            "files"
        ]

    def get_files(self, obj):
        request = self.context.get("request")
        return MaterialFileSerializer(
            obj.files.all(),
            many=True,
            context={"request": request}
        ).data

    def get_chapter_name(self, obj):
        if obj.chapter:
            return obj.chapter.title
        return obj.custom_chapter

    def get_subject_name(self, obj):
        if obj.subject:
            return obj.subject.name
        return None