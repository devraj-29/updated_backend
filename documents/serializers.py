from rest_framework import serializers
from .models import SignedDocument


class SignedDocListSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    docx_url = serializers.SerializerMethodField()

    class Meta:
        model = SignedDocument
        fields = [
            "id", "confirmation_id", "assignment",
            "signer_name", "signer_email", "signer_company",
            "signer_person_type", "signer_designation",
            "nda_name", "nda_category", "nda_version",
            "consent_timestamp", "ip_address",
            "signed_pdf", "pdf_url",
            "nda_copy_docx", "docx_url",
            "pdf_generated", "email_sent", "created_at",
        ]

    def _make_url(self, field):
        if not field:
            return None
        req = self.context.get("request")
        return req.build_absolute_uri(field.url) if req else field.url

    def get_pdf_url(self, obj):
        return self._make_url(obj.signed_pdf)

    def get_docx_url(self, obj):
        return self._make_url(obj.nda_copy_docx)


class SignedDocDetailSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    docx_url = serializers.SerializerMethodField()
    sig_url = serializers.SerializerMethodField()

    class Meta:
        model = SignedDocument
        fields = "__all__"

    def _make_url(self, field):
        if not field:
            return None
        req = self.context.get("request")
        return req.build_absolute_uri(field.url) if req else field.url

    def get_pdf_url(self, obj):
        return self._make_url(obj.signed_pdf)

    def get_docx_url(self, obj):
        return self._make_url(obj.nda_copy_docx)

    def get_sig_url(self, obj):
        return self._make_url(obj.signature_image)


class SignRequestSerializer(serializers.Serializer):
    signature_image_base64 = serializers.CharField()
    consent_text = serializers.CharField()
    signer_name_confirmation = serializers.CharField()
