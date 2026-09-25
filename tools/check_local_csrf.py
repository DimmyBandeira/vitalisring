"""Valida o ciclo CSRF local sem usar dados ou credenciais reais."""

import re

import httpx


def check_origin(base_url: str) -> tuple[int, int, bool]:
    with httpx.Client(base_url=base_url, follow_redirects=True) as client:
        page = client.get("/login")
        match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        if match is None:
            raise RuntimeError("Token CSRF não encontrado")
        response = client.post(
            "/login",
            data={"email": "nobody@example.test", "csrf_token": match.group(1)},
            headers={"Origin": base_url},
        )
    return page.status_code, response.status_code, "Confira seu e-mail" in response.text


def main() -> None:
    for base_url in ("http://localhost:8000", "http://127.0.0.1:8000"):
        get_status, post_status, requested_page = check_origin(base_url)
        print(base_url)
        print("GET_STATUS:", get_status)
        print("POST_STATUS:", post_status)
        print("REQUESTED_PAGE:", requested_page)


if __name__ == "__main__":
    main()
