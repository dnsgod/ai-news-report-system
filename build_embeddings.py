from services.vector_service import (
    create_missing_embeddings,
)


def main():
    print(
        "기사 임베딩 생성을 시작합니다."
    )

    result = create_missing_embeddings()

    print()
    print("기사 임베딩 생성 완료")
    print(
        f"성공: {result['created']}건"
    )
    print(
        f"실패: {result['failed']}건"
    )


if __name__ == "__main__":
    main()