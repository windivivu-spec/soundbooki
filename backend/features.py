"""Release gates. Pro Max is deferred until API costs are viable."""

PRO_MAX_ENABLED = False
TURBO_ENABLED = False


def require_local_model(model_id):
    if model_id == 'turbo' and not TURBO_ENABLED:
        raise ValueError('Turbo đã ngừng cung cấp. Chọn Nano để tạo nhanh hoặc giọng riêng F5 trong Pro.')


def require_pro_max():
    if not PRO_MAX_ENABLED:
        raise ValueError('Tính năng tạo sách qua API đang tạm hoãn. Hãy chọn giọng đọc local.')
