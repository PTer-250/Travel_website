"""Seed the database with demo diaries and media files."""

from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime
from typing import List

from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select

from app.core.db import get_session_maker
from app.models.diaries import Diary
from app.models.enums import DiaryMediaType, DiaryStatus, RegionType
from app.models.locations import Region
from app.models.users import User
from app.repositories.diaries import DiaryRepository
from app.schemas.diary import DiaryCreateRequest
from app.services.diary import DiaryService, PendingDiaryMedia
from app.services.media_storage import get_media_storage_service


SAMPLE_IMAGES = {
    "sunrise": base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAIElEQVR42mNgGAWjYBSMglEwCkbDqAEYDBgGDAaGJAAAjKABP1sBu/IAAAAASUVORK5CYII="
    ),
    "night": base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAIElEQVR42mNgGAU0A8QwCkbDqAEYDBgGDAaGJAAAJe0BO+hsBQgAAAAASUVORK5CYII="
    ),
}


async def ensure_demo_user(session) -> User:
    """Create (or fetch) a demo author."""

    email = "demo@travel.local"
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    helper = PasswordHelper()
    hashed = helper.hash("DemoPass123!")
    user = User(
        email=email,
        username="demo_author",
        hashed_password=hashed,
        interests=["自然", "美食"],
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def ensure_demo_region(session) -> Region:
    """Guarantee at least one region for the diaries."""

    result = await session.execute(select(Region).where(Region.name == "示例景区"))
    region = result.scalar_one_or_none()
    if region:
        return region

    region = Region(
        name="示例景区",
        type=RegionType.SCENIC,
        popularity=80,
        rating=4.6,
        description="用于演示日记功能的示例景区。",
        city="杭州",
        latitude=30.274085,
        longitude=120.15507,
    )
    session.add(region)
    await session.commit()
    await session.refresh(region)
    return region


def build_diary_payloads(region_id: int) -> List[dict]:
    """Prepare diary payload definitions."""

    timestamp = datetime.utcnow().strftime("%Y年%m月%d日")
    return [
        {
            "title": "初冬西湖日出",
            "content": (
                f"在{timestamp}清晨，与好友漫步苏堤，薄雾升腾时的日出让人惊叹。\n"
                "{{media:cover}}\n\n我们随后打卡了楼外楼早茶，热腾腾的馄饨配上桂花糕非常应景。"
            ),
            "tags": ["清晨", "摄影", "美食"],
            "media": [
                {
                    "placeholder": "cover",
                    "media_type": DiaryMediaType.IMAGE,
                    "filename": "sunrise.png",
                    "content_type": "image/png",
                    "data": SAMPLE_IMAGES["sunrise"],
                }
            ],
        },
        {
            "title": "断桥夜色慢行",
            "content": (
                "入夜后的湖面一点点亮起，远处的音乐喷泉与漫天星光相互映衬。\n"
                "{{media:night}}\n\n沿途还有咖啡车和街头歌手，氛围感直接拉满。"
            ),
            "tags": ["夜景", "散步"],
            "media": [
                {
                    "placeholder": "night",
                    "media_type": DiaryMediaType.IMAGE,
                    "filename": "night.png",
                    "content_type": "image/png",
                    "data": SAMPLE_IMAGES["night"],
                }
            ],
        },
    ]


async def seed(args) -> None:
    if not args.enable:
        print("[seed] 已禁用默认示例日记写入；如需写入请加 --enable")
        return

    maker = get_session_maker()
    async with maker() as session:
        if not args.force:
            existing = await session.scalar(select(func.count(Diary.id)))
            if existing:
                print(f"[seed] 检测到现有日记 {existing} 篇，如需强制写入请加 --force")
                return

        user = await ensure_demo_user(session)
        region = await ensure_demo_region(session)

        repo = DiaryRepository(session)
        storage = get_media_storage_service()
        service = DiaryService(repo, storage)

        for payload in build_diary_payloads(region.id):
            request = DiaryCreateRequest(
                title=payload["title"],
                content=payload["content"],
                region_id=region.id,
                tags=payload["tags"],
                media_placeholders=[],
                status=DiaryStatus.PUBLISHED,
            )
            uploads = [
                PendingDiaryMedia(
                    placeholder=media["placeholder"],
                    media_type=media["media_type"],
                    filename=media["filename"],
                    content_type=media["content_type"],
                    data=media["data"],
                )
                for media in payload["media"]
            ]
            diary, stats = await service.create_diary(user.id, request, uploads)
            print(f"[seed] 已创建日记《{diary.title}》，压缩: {stats['compressed']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo diaries with media files")
    parser.add_argument(
        "--enable",
        action="store_true",
        help="Actually seed the demo diaries (disabled by default)",
    )
    parser.add_argument("--force", action="store_true", help="Force seeding even if diaries exist")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(seed(args))


if __name__ == "__main__":
    main()
