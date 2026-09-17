from rest_framework import serializers

from questionnaire.models import QuestionnaireQuestion


class QuestionnaireQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireQuestion
        # `version` is deliberately omitted per-question -- it's returned
        # once at the questionnaire level (see QuestionnaireView), not
        # repeated on every question.
        fields = ["id", "key", "question_text", "question_type", "order", "options"]
        read_only_fields = fields


class QuestionnaireResponseInputSerializer(serializers.Serializer):
    """POST /api/questionnaire/{id}/response/'s input contract."""

    question_id = serializers.IntegerField()
    selected_value = serializers.CharField(max_length=60)
