from sqladmin import ModelView

from backend.infrastructure.persistence.models.social import Comment, Like


class CommentAdmin(ModelView, model=Comment):
    name = "Comment"
    name_plural = "Comments"
    category = "Social"
    column_list = [
        Comment.id,
        Comment.user_id,
        Comment.target_type,
        Comment.target_id,
        Comment.status,
        Comment.created_at,
    ]
    column_sortable_list = [Comment.created_at, Comment.status]
    form_excluded_columns = [Comment.created_at, Comment.updated_at, Comment.deleted_at]


class LikeAdmin(ModelView, model=Like):
    name = "Like"
    name_plural = "Likes"
    category = "Social"
    column_list = [Like.id, Like.user_id, Like.target_type, Like.target_id, Like.created_at]
    form_excluded_columns = [Like.created_at]
