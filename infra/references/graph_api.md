다음은 Microsoft Graph API를 활용한 메일 쿼리 모듈 구현 명세서에 OAuth 토큰 엔드포인트 형식, 사용자 인증 엔드포인트 형식, 메일 요청 엔드포인트 형식을 보완한 내용입니다.

-----

# Microsoft Graph API를 활용한 메일 쿼리 모듈 구현 명세서

## 1\. Microsoft Graph API 메일 작업 소개

이 문서는 Microsoft Graph API를 사용하여 메일 쿼리 모듈을 구현하는 개발자를 위한 포괄적인 기술 참조 자료입니다. Microsoft 365 메일 서비스와의 효율적이고 견고한 통합을 보장하기 위해 필요한 API 호출, 매개변수, 속성 및 모범 사례를 자세히 설명합니다.

Microsoft Graph는 Microsoft 365 서비스 전반의 데이터에 접근하기 위한 REST API 및 클라이언트 라이브러리를 노출하는 통합 프로그래밍 모델입니다.[1, 2] 이는 데이터 및 인텔리전스에 대한 게이트웨이 역할을 하며, Microsoft 365 경험을 확장하는 지능형 애플리케이션 개발을 가능하게 합니다.[2] API 구조는 `{HTTP 메서드} https://graph.microsoft.com/{버전}/{리소스}?{쿼리-매개변수}`와 같은 일관된 패턴을 따릅니다.[3]

모듈의 안정성을 고려할 때, 프로덕션 애플리케이션에는 **`v1.0` 엔드포인트 사용이 권장됩니다.**[3] `beta` 엔드포인트는 현재 미리 보기 상태의 API를 포함하며, 향후 호환성을 깨는 변경 사항이 발생할 수 있으므로 개발 및 테스트 용도로만 사용해야 합니다.[3] 이러한 버전 관리의 중요성은 모듈 설계의 핵심적인 부분입니다. 만약 특정 기능이 `beta` 버전에서만 제공된다면, 해당 기능은 실험적이거나 향후 리팩토링이 필요할 수 있음을 명세서에 명확히 표시하여 모듈의 장기적인 유지보수성과 신뢰성에 미치는 영향을 고려해야 합니다.

Microsoft Graph는 사용자의 기본 사서함과 공유 사서함에 있는 메일 데이터에 접근하는 것을 지원하며, 이 데이터는 Microsoft 365의 일부로 Exchange Online 클라우드에 저장됩니다.[4] Microsoft Graph가 "Microsoft 365의 데이터 및 인텔리전스에 대한 게이트웨이"이자 "통합 프로그래밍 모델"이라는 점은 중요한 의미를 가집니다.[1, 2] 이는 개발자가 여러 개의 분리된 서비스별 API를 학습할 필요 없이 단일 통합 엔드포인트를 통해 접근할 수 있어 통합 프로세스가 단순화됨을 의미합니다. 이러한 통합된 접근 방식은 메일 기능뿐만 아니라 캘린더, 연락처 등 Microsoft 365의 다른 요소들과 메일을 연결하여 더욱 지능적이고 상호 연결된 애플리케이션을 구축할 수 있는 기반을 제공합니다.

-----

## 2\. 메일 접근을 위한 인증 및 권한 부여

Microsoft Graph API와 상호 작용하려면 애플리케이션이 Azure Active Directory(Azure AD) 포털에 먼저 등록되어야 합니다.[1] 등록 후, 애플리케이션에 메일 데이터에 접근하는 데 필요한 **권한(스코프)을 부여하는 것이 필수적입니다.** 이메일 읽기를 위해서는 `Mail.Read` 권한이 필요하며, `Mail.ReadBasic`은 기본적인 읽기 접근 권한을 제공합니다.[1, 5] 이메일 전송을 위해서는 `Mail.Send` 권한이 요구됩니다.[6]

권한은 **위임된 권한**(직장/학교 계정 또는 개인 Microsoft 계정용) 또는 **애플리케이션 권한**(로그인한 사용자 없이 모든 사용자의 사서함에 접근하는 백그라운드 서비스용)으로 부여될 수 있습니다.[5, 6] PowerShell 사용자는 `(Get-MgContext).Scopes` 명령을 사용하여 현재 권한을 확인할 수 있습니다.[7]

인증은 **OAuth 2.0을 통해 처리됩니다.** 웹 애플리케이션에서 접근 토큰을 얻기 위한 일반적인 방법은 **권한 부여 코드 흐름**입니다.[1] 이 과정에는 사용자를 Microsoft 로그인 페이지로 리디렉션하여 동의를 얻은 후, 권한 부여 코드를 접근 토큰으로 교환하는 단계가 포함됩니다.[1]

**앱 등록 시 얻은 클라이언트 ID와 비밀**은 접근 토큰과 함께 요청을 인증하는 데 필수적입니다.[1] 접근 토큰은 일반적으로 59분 이내에 만료되므로 [7], 지속적인 접근을 유지하기 위한 **견고한 토큰 갱신 메커니즘**이 필요합니다. 보안 강화를 위해 앱 비밀과 관련된 문제를 피하려면, 인증서 기반 인증을 고려하는 것이 유용합니다.[7]

문서에서 `Mail.ReadBasic`을 "최소 권한"으로, `Mail.Read`를 "더 높은 권한"으로 명시하는 것은 단순한 옵션 목록을 넘어선 보안 모범 사례를 나타냅니다.[5, 6] 모듈은 항상 기능에 필요한 **최소한의 권한**을 요청해야 합니다. 예를 들어, `Mail.ReadBasic`으로 충분한데 `Mail.Read`와 같이 과도한 권한을 요청하는 것은 공격 표면을 증가시키고 사용자 동의 과정에서 마찰을 일으킬 수 있습니다. 따라서 개발자는 모듈의 정확한 요구 사항을 면밀히 분석하여 보안 원칙과 기능을 균형 있게 유지하는 가장 적절하고 최소한의 권한 집합을 선택해야 합니다.

접근 토큰의 59분 만료 시간은 [7] 단순한 시간 제한이 아니라 중요한 운영 제약 조건입니다. 토큰을 사전에 갱신하지 못하면 빈번한 `401 Unauthorized` 오류가 발생하여 [7] 모듈 운영이 중단될 수 있습니다. 이는 모듈 설계에 지속적인 서비스 보장을 위한 **견고한 백그라운드 토큰 갱신 메커니즘**(예: 갱신 토큰 사용)이 포함되어야 함을 의미합니다. 이는 단순한 오류 처리를 넘어선 사전 예방적 복원력 전략으로, 프로덕션 수준 시스템에 필수적인 요소입니다.

### 2.1. 인증 엔드포인트 형식

Microsoft Graph API의 인증 흐름에서 사용되는 주요 엔드포인트는 다음과 같습니다.

#### **사용자 인증 엔드포인트 형식 (OAuth 2.0 권한 부여 엔드포인트)**

사용자가 애플리케이션에 대한 동의를 제공하고 권한 부여 코드를 얻는 데 사용됩니다.

  * **일반적인 형식:**
    `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`

      * `{tenant}`: Azure AD 테넌트 ID (GUID), 또는 `common` (다중 테넌트 앱의 경우), `organizations` (조직 계정만 허용), `consumers` (개인 Microsoft 계정만 허용).

  * **예시 (Common 엔드포인트):**
    `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={your_client_id}&response_type=code&redirect_uri={your_redirect_uri}&response_mode=query&scope={your_scopes}&state={your_state}`

      * `client_id`: Azure AD 앱 등록 시 발급받은 클라이언트 ID
      * `response_type`: 요청하는 응답 타입 (e.g., `code` for authorization code flow)
      * `redirect_uri`: 인증 후 리디렉션될 URL (앱 등록 시 설정된 URI 중 하나)
      * `response_mode`: 응답을 반환하는 방식 (e.g., `query`, `form_post`)
      * `scope`: 요청할 권한 (e.g., `Mail.Read`, `User.Read`, `offline_access`)
      * `state`: CSRF 방지 및 상태 유지를 위한 임의 문자열

#### **OAuth 토큰 엔드포인트 형식**

권한 부여 코드를 접근 토큰(Access Token), 갱신 토큰(Refresh Token), ID 토큰(ID Token)으로 교환하는 데 사용됩니다.

  * **일반적인 형식:**
    `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`

      * `{tenant}`: Azure AD 테넌트 ID (GUID), `common`, `organizations`, `consumers` 중 하나.

  * **예시 (POST 요청):**

    ```http
    POST https://login.microsoftonline.com/common/oauth2/v2.0/token
    Content-Type: application/x-www-form-urlencoded

    client_id={your_client_id}
    &scope={your_scopes}
    &code={authorization_code_from_authorize_endpoint}
    &redirect_uri={your_redirect_uri}
    &grant_type=authorization_code
    &client_secret={your_client_secret_or_certificate}
    ```

      * `grant_type`: 사용하려는 OAuth 2.0 흐름 (e.g., `authorization_code`, `refresh_token`, `client_credentials`)
      * `code`: 권한 부여 엔드포인트에서 받은 권한 부여 코드
      * `client_secret`: Azure AD 앱 등록 시 발급받은 클라이언트 비밀 (또는 인증서 사용)

-----

## 3\. 핵심 메일 API 엔드포인트 및 메시지 리소스

로그인한 사용자의 이메일을 가져오는 기본 엔드포인트는 `https://graph.microsoft.com/v1.0/me/messages`입니다.[1] 적절한 권한이 있다면 다른 사용자의 메시지나 특정 메일 폴더 내의 메시지에 접근하기 위한 다양한 변형이 있습니다:

  * `/users/{id | userPrincipalName}/messages/{id}` [5]
  * `/me/mailFolders/{id}/messages/{id}` [5]
  * `/users/{id | userPrincipalName}/mailFolders/{id}/messages/{id}` [5]
    이러한 `GET` 요청은 메시지 객체의 속성과 관계를 검색합니다.[5]

메시지의 원본 MIME 콘텐츠를 얻으려면 메시지 검색 엔드포인트에 `/$value` 매개변수를 추가할 수 있습니다: `GET /me/messages/{id}/$value`.[5] 이 경우 메시지 리소스가 아닌 MIME 형식의 메시지 콘텐츠가 반환됩니다.[5]

이미 존재하는 임시 메시지를 보내려면 `POST /me/messages/{id}/send` 또는 `POST /users/{id | userPrincipalName}/messages/{id}/send` 엔드포인트를 사용합니다.[6] 이 메서드는 성공 시 `202 Accepted` 응답 코드를 반환하며 응답 본문에는 아무것도 반환하지 않습니다.[6] `Authorization` 헤더에 `Bearer {token}`이 필요합니다.[6]

### 3.1. 메일 요청 엔드포인트 형식

메일 작업을 위한 주요 Microsoft Graph API 엔드포인트 형식은 다음과 같습니다.

  * **로그인한 사용자의 메시지 가져오기:**
    `GET https://graph.microsoft.com/v1.0/me/messages`

  * **특정 사용자의 메시지 가져오기 (관리자 또는 위임된 권한):**
    `GET https://graph.microsoft.com/v1.0/users/{user_id_or_upn}/messages`

      * `{user_id_or_upn}`: 사용자의 ID (GUID) 또는 UPN (User Principal Name)

  * **특정 메일 폴더의 메시지 가져오기:**
    `GET https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages`
    `GET https://graph.microsoft.com/v1.0/users/{user_id_or_upn}/mailFolders/{folder_id}/messages`

      * `{folder_id}`: 메일 폴더의 ID (예: `inbox`, `sentitems`, `drafts` 등)

  * **특정 메시지 가져오기:**
    `GET https://graph.microsoft.com/v1.0/me/messages/{message_id}`
    `GET https://graph.microsoft.com/v1.0/users/{user_id_or_upn}/messages/{message_id}`

      * `{message_id}`: 특정 메시지의 고유 ID

  * **메시지 전송 (초안 메시지 전송):**
    `POST https://graph.microsoft.com/v1.0/me/messages/{message_id}/send`
    `POST https://graph.microsoft.com/v1.0/users/{user_id_or_upn}/messages/{message_id}/send`

  * **새 메시지 생성 및 전송 (한 번의 요청으로 초안 생성 및 전송):**
    `POST https://graph.microsoft.com/v1.0/me/sendMail`
    `POST https://graph.microsoft.com/v1.0/users/{user_id_or_upn}/sendMail`

      * **요청 본문 예시:**
        ```json
        {
          "message": {
            "subject": "Hello from Graph API",
            "body": {
              "contentType": "Text",
              "content": "This is a test email sent via Microsoft Graph."
            },
            "toRecipients": [
              {
                "emailAddress": {
                  "address": "recipient@example.com"
                }
              }
            ]
          },
          "saveToSentItems": "true"
        }
        ```

  * **메시지 업데이트 (패치):**
    `PATCH https://graph.microsoft.com/v1.0/me/messages/{message_id}`

      * **요청 본문 예시 (메시지 읽음 상태 변경):**
        ```json
        {
          "isRead": true
        }
        ```

`message` 리소스는 메일 쿼리 모듈에 필수적인 풍부한 속성 집합을 노출합니다. 주요 속성은 다음과 같습니다 [8, 9, 10]:

  * `id`: 메시지의 고유 식별자 (읽기 전용). `Prefer: IdType="ImmutableId"` 헤더를 사용하면 이동 시에도 변경되지 않도록 할 수 있습니다.[10]
  * `subject`: 메시지의 제목 줄.
  * `from`: 발신자의 이메일 주소.
  * `receivedDateTime`: 메시지가 수신된 날짜 및 시간 (UTC).
  * `sentDateTime`: 메시지가 전송된 날짜 및 시간 (UTC).
  * `body`: HTML 또는 텍스트 형식의 본문 내용. `Prefer: outlook.body-content-type` 헤더로 형식을 지정할 수 있습니다.[5, 10]
  * `bodyPreview`: 메시지 본문의 첫 255자 (텍스트 형식).
  * `hasAttachments`: 메시지에 첨부 파일이 있는지 여부를 나타내는 부울 값 (인라인 첨부 파일은 제외).[10]
  * `isRead`: 메시지가 읽혔는지 여부를 나타내는 부울 값.
  * `importance`: 메시지의 중요도 (`low`, `normal`, `high`).
  * `parentFolderId`: 메시지의 상위 메일 폴더의 고유 식별자.
  * `conversationId`: 이메일이 속한 대화의 ID.
  * `webLink`: Outlook 웹에서 메시지를 여는 URL.
  * `toRecipients`, `ccRecipients`, `bccRecipients`, `replyTo`: 수신자 이메일 주소 컬렉션.
  * `internetMessageHeaders`: RFC5322 메시지 헤더 컬렉션. `$select`와 함께 사용될 때만 반환됩니다.[10]

`message` 리소스는 또한 사용자 지정 속성 및 데이터를 위한 확장 기능을 지원합니다.[5]

`body`와 `bodyPreview` 속성이 모두 존재하는 것은 [8, 9, 10] 단순한 중복이 아니라 성능 최적화를 위한 기회를 제공합니다. `bodyPreview`는 잠재적으로 큰 전체 `body` 콘텐츠를 가져오지 않고도 메시지의 빠른 요약을 제공합니다. 메일 쿼리 모듈의 주요 사용 사례가 스니펫과 함께 이메일 목록을 표시하는 경우, **`bodyPreview`만 가져오는 것은 페이로드 크기를 크게 줄이고 응답 시간을 향상시킵니다.** 사용자가 이메일을 명시적으로 열 때만 전체 `body`를 요청하는 것이 성능 최적화 전략입니다.

메시지의 `id` 속성은 `Prefer: IdType="ImmutableId"` 헤더를 사용하지 않는 한 [10] 메시지가 폴더 간에 이동될 때 변경됩니다. 이는 미묘하지만 중요한 세부 사항입니다. 메일 쿼리 모듈이 특정 메시지에 대한 영구적인 참조(예: 추적, 보관 또는 연결용)를 유지해야 하는 경우, 기본 `id`에 의존하는 것은 불안정합니다. 이는 모듈이 안정적인 메시지 식별자가 필요한 모든 시나리오에서 **`ImmutableId` 헤더를 처음부터 구현해야 함**을 의미합니다. 이는 데이터 무결성 문제를 방지하고 모듈 내에서 장기적인 데이터 관리를 단순화합니다.

**표 1: 메일 메시지 리소스의 주요 속성**

| 속성 이름 | 유형 | 설명 | 참고 사항 | 출처 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `String` | 메시지의 고유 식별자. | 읽기 전용. `Prefer: IdType="ImmutableId"`를 사용하지 않으면 이동 시 변경됨. | [8, 10] |
| `subject` | `String` | 메시지의 제목. | | [8, 10] |
| `from` | `Recipient` | 메시지 발신자. | | [8, 10] |
| `receivedDateTime` | `DateTimeOffset` | 메시지가 수신된 날짜 및 시간 (UTC). | | [8, 10] |
| `sentDateTime` | `DateTimeOffset` | 메시지가 전송된 날짜 및 시간 (UTC). | | [9, 10] |
| `body` | `ItemBody` | 본문 내용 (HTML/텍스트). | `Prefer: outlook.body-content-type`로 형식을 지정할 수 있음. | [5, 8, 10] |
| `bodyPreview` | `String` | 본문의 첫 255자 (텍스트). | 빠른 미리 보기에 유용. | [8, 10] |
| `hasAttachments` | `Boolean` | 메시지에 첨부 파일이 있는지 여부. | 인라인 첨부 파일은 포함되지 않음. | [8, 10] |
| `isRead` | `Boolean` | 메시지가 읽혔는지 여부. | | [8, 10] |
| `importance` | `Importance` | 메시지의 중요도 (`low`, `normal`, `high`). | | [8, 10] |
| `parentFolderId` | `String` | 상위 메일 폴더의 ID. | | [8, 10] |
| `conversationId` | `String` | 대화의 ID. | | [8, 10] |
| `webLink` | `String` | Outlook 웹에서 메시지를 여는 URL. | | [9, 10] |
| `toRecipients` | `Recipient collection` | To: 수신자. | | [9, 10] |
| `ccRecipients` | `Recipient collection` | Cc: 수신자. | | [8, 10] |
| `bccRecipients` | `Recipient collection` | Bcc: 수신자. | | [8, 10] |
| `internetMessageHeaders` | `InternetMessageHeader collection` | RFC5322 메시지 헤더. | `$select`와 함께 사용될 때만 반환됨. | [8, 10] |

-----

## 4\. 메일 데이터의 고급 쿼리 및 필터링 (OData 매개변수)

Microsoft Graph는 `$filter`, `$search`, `$select`, `$orderby`, `$top`, `$skip`, `$count`와 같은 다양한 OData 시스템 쿼리 매개변수를 지원하여 응답으로 반환되는 데이터의 양과 유형을 제어할 수 있습니다.[11] `beta` 엔드포인트에서는 `$` 접두사가 선택 사항이지만, 모든 버전에서 일관성을 위해 항상 `$`를 포함하는 것이 모범 사례입니다.[11]

### 필터링 (`$filter`)

`$filter` 매개변수는 각 리소스에 대한 표현식을 평가하여 컬렉션의 하위 집합을 검색할 수 있도록 합니다.[12] 표현식이 `true`로 평가되는 항목만 포함됩니다.

  * **발신자별 필터링:** `GET ~/me/messages?$filter=from/emailAddress/address eq 'someuser@example.com'`.[12]
  * **제목별 필터링:** `subject eq 'Major update from Message center'`와 같이 사용할 수 있습니다.[13] 부분 일치를 위해서는 `contains` 함수도 사용할 수 있습니다.[12]
  * **날짜 범위별 필터링:** `GET ~/me/mailFolders/inbox/messages?$filter=ReceivedDateTime ge 2017-04-01 and receivedDateTime lt 2017-05-01`.[12] 날짜는 ISO 8601 형식이어야 합니다.[8]
  * **읽음 상태별 필터링:** `GET ~/me/mailFolders/inbox/messages?$filter=isRead eq false`.[12]
  * **첨부 파일별 필터링:** `GET /v1.0/me/mailfolders/inbox/messages?$filter=(hasAttachments eq true OR hasAttachments eq false)`.[14] 이는 첨부 파일이 있거나 없는 메시지를 필터링할 수 있도록 합니다.
  * **중요도별 필터링:** `importance` 속성은 `eq` 연산자를 지원합니다.[15, 16] 예: `importance eq 'high'`.[8]
  * **논리 연산자를 사용한 필터 결합:** 필터는 `and`, `or`, `not`을 사용하여 결합할 수 있습니다.[12]
  * **`$filter` 복잡성 및 성능 고려 사항:** 여러 속성 또는 `orderby` 절을 포함하는 복잡한 필터는 `InefficientFilter` 오류를 유발할 수 있습니다.[13]
  * **`ConsistencyLevel`을 사용한 고급 필터링:** 일부 고급 필터링 시나리오에서는 `ConsistencyLevel = eventual` 헤더가 필요할 수 있습니다.[15] 이는 쿼리 결과의 최종 일관성을 나타냅니다.

`$filter`와 `$orderby`를 복잡한 조건과 함께 사용할 때 발생하는 `InefficientFilter` 오류는 [13] 기본 쿼리 최적화 프로그램의 한계를 직접적으로 보여줍니다. 이는 단순한 오류가 아니라 성능 병목 현상을 나타내는 지표입니다. 이러한 매개변수를 결합하기 위한 규칙은 [13, 14] 임의적인 것이 아니라 서버 측에서 효율적인 인덱싱 및 쿼리 실행을 가능하게 하기 위해 정해진 것입니다. 따라서 모듈 개발자는 이러한 규칙을 엄격히 준수하여 쿼리를 신중하게 설계해야 하며, **`InefficientFilter` 오류가 계속 발생할 경우 다른 전략(예: 데이터셋이 작을 경우 클라이언트 측 정렬 또는 복잡한 쿼리 분할)을 고려해야 합니다.**

### 검색 (`$search`)

`$search` 매개변수는 메시지 컬렉션에 대한 전체 텍스트 검색 기능을 제공합니다.[16, 17]

  * **검색 가능한 속성:** `attachment`, `bcc`, `body`, `cc`, `from`, `hasAttachment`, `importance`, `kind`, `participants`, `received`, `recipients`, `sent`, `size`, `subject`, `to`를 포함한 광범위한 속성이 검색 가능합니다.[16]
  * **`$search` 절의 구문:** 구문은 `"<property>:<text to search>"`입니다. 전체 절은 이중 따옴표 안에 있어야 합니다. 이중 따옴표나 백슬래시가 포함된 경우 백슬래시로 이스케이프해야 하며, 다른 특수 문자는 URL 인코딩되어야 합니다.[16]
  * **`$search`의 제한 사항:** 중요한 제한 사항은 `$search` 쿼리가 일반적으로 최대 250개의 레코드만 가져오며 `$skip` 매개변수를 지원하지 않는다는 것입니다.[13] 또한 `search/query` API(POST 요청)는 특정 폴더에서 결과를 가져오는 것을 지원하지 않습니다.[13]

### 속성 선택 (`$select`)

`$select` 쿼리 옵션은 클라이언트가 특정 속성 집합을 요청할 수 있도록 하여, 전송되는 데이터 양을 줄여 응답 페이로드를 최적화합니다.[11] 예: `?$select=id,receivedDateTime,subject,from`.[13]

### 결과 정렬 (`$orderby`)

`$orderby` 매개변수는 클라이언트가 특정 순서로 리소스를 요청할 수 있도록 합니다.[11]

  * **`receivedDateTime`, `subject`, `from`, `hasAttachments`별 정렬:** `receivedDateTime DESC`, `from/emailAddress/address`, `hasAttachments`와 같은 예시가 있습니다.[13, 14]
  * **`$orderby`와 `$filter` 결합 규칙:** 메시지 쿼리에서 `$filter`와 `$orderby`를 함께 사용할 때 오류를 피하기 위해 특정 규칙을 따라야 합니다 [13, 14]:
    1.  `$orderby`에 나타나는 속성은 `$filter`에도 나타나야 합니다.
    2.  `$orderby`에 나타나는 속성은 `$filter`와 동일한 순서로 나타나야 합니다.
    3.  `$orderby`에 있는 속성은 `$filter`에서 `$orderby`에 없는 다른 속성보다 *먼저* 나타나야 합니다.

### 결과 개수 (`$count`)

`$count` 매개변수는 일치하는 리소스의 총 개수를 검색합니다.[11] 이는 종종 페이지 매김을 위해 `$top`과 함께 사용됩니다.[11] 디렉터리 리소스에 대한 페이지 매김 시 `$count`는 페이지 결과 집합의 첫 페이지에서만 반환됩니다.[18]

`$filter`와 `$search`는 모두 결과를 좁히는 방법을 제공하지만, 뚜렷한 기능과 제한 사항을 가지고 있습니다. `$filter`는 OData 연산자(eq, ge, lt 등)를 사용하여 정확하며 페이지 매김을 위한 `$skip`을 지원하지만 [11, 12] 복잡할 수 있습니다. `$search`는 여러 속성에 대한 전체 텍스트 검색을 제공하지만 [16, 17] 엄격한 250개 레코드 제한이 있으며 `$skip`을 지원하지 않습니다.[13] 이는 중요한 아키텍처적 결정을 의미합니다. 정확하고 페이지 매김된 결과를 위해서는 `$filter`가 우수합니다. 광범위한 키워드 기반 검색을 위해서는 `$search`가 유용하지만, 초기 제한된 결과 집합에만 해당됩니다. 모듈은 `$search`를 초기 검색에 사용하고 `$filter`를 상세한 페이지 매김된 보기에 사용하거나, 구조화된 쿼리에는 `$filter`만 사용하는 등 **이들을 결합하여 활용할 수 있습니다.** 이는 특정 사용자 상호 작용 패턴에 기반한 데이터 검색에 대한 미묘한 접근 방식을 강조합니다.

**표 2: 메일 작업용 OData 쿼리 매개변수**

| 매개변수 | 설명 | 메일 예시 | 참고 사항 |출처 |
| :--- | :--- | :--- | :--- | :--- |
| `$filter` | 지정된 기준에 따라 결과를 필터링. | `?$filter=isRead eq false and receivedDateTime ge 2024-01-01T00:00:00Z` | 다양한 연산자 지원 (`eq`, `ne`, `gt`, `lt`, `ge`, `le`, `startswith`, `endswith`, `contains`, `in`, `and`, `or`, `not`). `$orderby`와 결합 시 규칙 적용. | [12, 13, 14] |
| `$search` | 전체 텍스트 검색 기준에 따라 결과 반환. | `?$search="subject:report"&$select=subject` | 약 250개 레코드로 제한. `$skip` 미지원. 구문: `"<property>:<text>"`. | [13, 16, 17] |
| `$select` | 응답에 반환할 특정 속성 선택. | `?$select=id,subject,from,receivedDateTime` | 페이로드 크기 최적화. `internetMessageHeaders`에 필수. | [11, 13] |
| `$orderby` | 지정된 속성별로 결과 정렬 (오름차순/내림차순). | `?$orderby=receivedDateTime DESC` | 속성은 `$filter`에도 나타나야 하며 특정 순서 규칙을 따라야 함. | [11, 13, 14] |
| `$top` | 단일 페이지에 반환할 최대 항목 수 설정. | `?$top=50` | 클라이언트 측 페이지 매김에 사용. 최대 페이지 크기는 API별로 다름. | [11, 18] |
| `$skip` | 결과 집합에서 지정된 수의 항목 건너뛰기. | `?$skip=50` | 클라이언트 측 페이지 매김에 사용. `$search`와 함께 사용 불가. | [11, 13] |
| `$skiptoken` | 서버 측 페이지 매김에 사용되어 다음 페이지 결과 검색. | `@odata.nextLink` URL에 포함됨. | 추출하여 다른 요청에 재사용 금지. | [18, 19] |
| `$count` | 일치하는 리소스의 총 개수 검색. | `?$count=true` | 디렉터리 리소스의 경우 첫 페이지에서만 반환됨. | [11, 18] |

**표 4: `$search`를 사용한 메일 메시지 검색 가능 속성**

| 검색 가능 속성 | 설명 | 예시 쿼리 | 출처 |
| :--- | :--- | :--- | :--- |
| `attachment` | 이메일에 첨부된 파일 이름. | `GET../me/messages?$search="attachment:report.pdf"` | [16] |
| `bcc` | Bcc 필드 (SMTP 주소, 표시 이름 또는 별칭). | `GET../me/messages?$search="bcc:samanthab@contoso.com"` | [16] |
| `body` | 이메일 메시지의 본문. | `GET../me/messages?$search="body:invoice"` | [16] |
| `cc` | Cc 필드 (SMTP 주소, 표시 이름 또는 별칭). | `GET../me/messages?$search="cc:danas"` | [16] |
| `from` | 이메일 메시지 발신자 (SMTP 주소, 표시 이름 또는 별칭). | `GET../me/messages?$search="from:randiw"` | [16] |
| `hasAttachment` | 인라인 첨부 파일이 아닌 첨부 파일이 있는 경우 `true`, 그렇지 않으면 `false`. | `GET../me/messages?$search="hasAttachments:true"` | [16] |
| `importance` | 메시지의 중요도 (`low`, `medium`, `high`). | `GET../me/messages?$search="importance:high"` | [16] |
| `kind` | 메시지 유형 (예: `email`, `meetings`, `voicemail`). | `GET../me/messages?$search="kind:email"` | [16] |
| `participants` | `from`, `to`, `cc`, `bcc` 필드. | `GET../me/messages?$search="participants:danas"` | [16] |
| `received` | 메시지가 수신된 날짜. | `GET../me/messages?$search="received:07/23/2018"` | [16] |
| `recipients` | `to`, `cc`, `bcc` 필드. | `GET../me/messages?$search="recipients:randiq"` | [16] |
| `sent` | 메시지가 발신자에 의해 전송된 날짜. | `GET../me/messages?$search="sent:07/23/2018"` | [16] |
| `size` | 항목의 크기 (바이트). | `GET../me/messages?$search="size:1..500000"` | [16] |
| `subject` | 제목 줄의 텍스트. | `GET../me/messages?$search="subject:meeting"` | [16] |
| `to` | To 필드 (SMTP 주소, 표시 이름 또는 별칭). | `GET.../me/messages?$search="to:randiw"` | [16] |

-----

## 5\. 대규모 데이터셋 처리 (페이지 매김)

페이지 매김은 Microsoft Graph에서 대규모 데이터셋을 효율적으로 처리하고 애플리케이션 성능 및 응답 시간을 향상시키는 데 필수적인 성능 기법입니다.[18] 일부 `GET` 쿼리는 서버 측 페이지 매김 또는 클라이언트 측 페이지 매김으로 인해 여러 페이지의 데이터를 반환합니다.[18]

### `@odata.nextLink`를 사용한 서버 측 페이지 매김

Microsoft Graph 서비스는 클라이언트가 지정하지 않아도 페이지당 기본 수의 결과를 반환하는 경우가 많습니다 (예: `/users` 엔드포인트의 경우 100개).[18] 추가 데이터 페이지가 있는 경우, 응답에는 다음 페이지 결과의 URL을 포함하는 **`@odata.nextLink` 속성**이 포함됩니다.[18, 19] 모든 결과를 검색하려면 애플리케이션은 이 속성이 더 이상 반환되지 않을 때까지 각 응답에서 제공된 `@odata.nextLink` URL을 사용하여 Microsoft Graph를 계속 호출해야 합니다.[18, 19]

### `$top` 및 `$skip`을 사용한 클라이언트 측 페이지 매김

클라이언트 애플리케이션은 `$top` 쿼리 매개변수를 사용하여 페이지당 원하는 결과 수를 지정할 수 있습니다.[18] `$skip` 매개변수는 특정 수의 항목을 건너뛰는 데 사용될 수 있으며, 종종 특정 페이지를 검색하기 위해 `$top`과 결합됩니다.[11] 그러나 `$top` 및 `$skip` 지원은 API마다 다릅니다. 예를 들어, `$search`와 함께 `$skip`은 지원되지 않습니다.[13]

### 효율적인 페이지 매김을 위한 `$skiptoken` 이해

`@odata.nextLink` URL 값은 API에 따라 `$skiptoken` 또는 `$skip` 쿼리 매개변수를 포함하는 경우가 많습니다.[18] **`$skiptoken` 또는 `$skip` 값을 추출하여 수동으로 구성된 다른 요청에 사용하지 않는 것이 중요합니다.** 제공된 전체 `@odata.nextLink` URL을 사용해야 합니다.[18]

### 페이지 매김된 결과 반복을 위한 모범 사례

  * Microsoft Graph가 제공하는 전체 `@odata.nextLink` URL을 항상 다음 페이지 요청에 사용해야 합니다.[18]
  * `DirectoryPageTokenNotFoundException` 오류를 피하려면 *마지막으로 성공한 응답*에서 얻은 토큰을 다음 페이지 요청에 유지해야 합니다. 이는 재시도 작업에서 얻은 토큰을 사용하면 발생할 수 있는 오류를 방지합니다.[18]
  * 디렉터리 리소스의 경우 사용자 지정 요청 헤더(예: `ConsistencyLevel`)는 후속 페이지 요청에 자동으로 포함되지 않으므로 명시적으로 설정해야 한다는 점을 인지해야 합니다.[18]
  * `@odata.count` 속성( `$count=true` 사용 시)은 디렉터리 리소스의 페이지 결과 집합의 첫 페이지에서만 반환됩니다.[18]

재시도 작업에서 얻은 토큰을 사용할 경우 `DirectoryPageTokenNotFoundException`이 발생할 수 있다는 경고는 [18] 미묘하지만 중요한 세부 사항입니다. 이는 단순한 네트워크 오류 재시도 메커니즘이 의도치 않게 페이지 매김을 손상시킬 수 있음을 의미합니다. 모듈의 페이지 매김 로직은 중간에 실패하거나 재시도된 시도에서 얻은 토큰이 아닌, **`마지막으로 성공적으로 처리된 페이지`에서 얻은 토큰만 저장하고 사용하도록 설계되어야 합니다.** 이는 연속성을 보장하고 디버깅하기 어려운 종류의 오류를 방지하는 데 중요하며, 대규모 데이터셋을 안정적으로 처리하는 데 필수적입니다.

서버 측 및 클라이언트 측 페이지 매김의 구별, 그리고 API마다 `$top`/`$skip` 지원이 다른 점은 [18] 모든 페이지 매김에 적용되는 단일 솔루션이 없음을 나타냅니다. 메일의 경우 `me/messages`는 `$top`과 `$skip`을 지원하지만 [11], `$search`는 `$skip`을 지원하지 않습니다.[13] 이는 모듈의 페이지 매김 전략이 적응형이어야 함을 의미합니다. 일반 메시지 검색의 경우 클라이언트 측 `$top`/`$skip`이 사용될 수 있지만, 검색 결과의 경우 모듈은 250개 레코드 제한을 처리하고 해당 제한된 집합에 대해 자체 클라이언트 측 필터링/페이지 매김을 구현하거나 더 많은 결과가 필요한 경우 다른 API로 전환해야 할 수 있습니다. 이는 유연하고 상황 인지적인 페이지 매김 구현의 필요성을 강조합니다.

-----

## 6\. 오류 처리 및 문제 해결

Microsoft Graph API는 요청 결과를 나타내기 위해 표준 HTTP 상태 코드를 반환합니다.[7, 20]

  * `400 Bad Request`: 요청이 잘못되었거나 형식이 올바르지 않습니다.[7, 20] 구문이나 매개변수를 수정해야 합니다.
  * `401 Unauthorized`: 호출자가 인증되지 않았으며, 종종 접근 토큰이 없거나 만료되었을 때 발생합니다.[7, 20] 새 토큰을 얻어야 합니다.
  * `403 Forbidden`: 호출자가 작업을 수행할 권한이 없거나 동의가 누락되었습니다.[7, 20] Azure AD에서 필요한 권한을 추가해야 합니다.
  * `404 Not Found`: 리소스를 찾을 수 없거나 엔드포인트/리소스 ID가 유효하지 않습니다.[7, 20] URL과 ID를 확인해야 합니다.
  * `429 Too Many Requests`: 애플리케이션 또는 사용자가 속도 제한을 초과하여 스로틀링되었습니다.[7, 20, 21, 22]
  * `500 Internal Server Error`: 내부 서버 오류가 발생했습니다.[7, 20] 잠시 기다린 후 다시 시도해야 합니다.
  * `501 Not Implemented`: 요청된 기능이 구현되지 않았습니다.[20]
  * `503 Service Unavailable`: 서비스가 사용 불가능합니다.[7, 20] 서비스 상태를 확인하고 나중에 다시 시도해야 합니다.
  * `504 Gateway Timeout`: 서버가 프록시 역할을 하는 동안 업스트림 서버로부터 적시에 응답을 받지 못했습니다.[7, 20] `$search`와 같은 무거운 요청에서 자주 발생합니다.[7]

오류 응답은 일반적으로 JSON 형식으로 제공되며, 상세한 디버깅을 위해 `code`, `message`, `innerError` 필드를 포함합니다.[7]

### 지수 백오프를 통한 견고한 재시도 로직 구현

429(스로틀링) 및 5xx(서버 문제) 오류의 경우 **재시도 로직을 구현하는 것이 중요합니다.**[7, 22] 429 응답의 `Retry-After` 헤더는 제안된 대기 시간을 초 단위로 제공합니다.[7, 22] 이 지연 시간을 준수하는 것이 스로틀링에서 가장 빠르게 복구하는 방법입니다.[22] `Retry-After` 헤더가 제공되지 않으면 지수 백오프 재시도 정책이 권장됩니다.[22] 모든 요청이 사용량 제한에 누적되므로 즉각적인 재시도는 피해야 합니다.[21, 22]

### 권한 및 토큰 문제 진단을 위한 전략

401 오류의 경우 토큰 유효성을 확인하고 만료된 경우 갱신해야 합니다.[7] 403 오류의 경우 필요한 권한 스코프를 검토하고 Azure AD에서 부여되었는지 확인해야 합니다. 애플리케이션 권한의 경우 관리자 승인이 필요할 수 있습니다.[7] 각 API 호출에 `client-request-id` 헤더(GUID)를 추가하여 추적 및 디버깅을 개선하는 것이 좋습니다.[7] 특정 오류 메시지를 캡처하기 위해 API 호출을 try/catch 블록으로 묶어야 합니다.[7] 코드를 작성하기 전에 Graph Explorer(`aka.ms/ge`)를 사용하여 API 호출을 테스트하고 필요한 권한을 확인하는 것이 유용합니다.[7]

문서에서 401 및 403 오류를 *처리하는* 방법(토큰 갱신, 권한 추가)을 자세히 설명하지만, 동시에 이러한 오류를 *방지하는* 방법을 암시적으로 제안합니다. `(Get-MgContext).Scopes`를 사용하여 권한을 확인하고 [7] Graph Explorer를 사용하여 배포 전에 권한을 확인하는 것에 대한 강조는 [7] 반응적 디버깅에서 사전 예방적 유효성 검사로의 전환을 나타냅니다. 모듈 구현의 경우, 이는 런타임 오류를 기다리지 않고 **개발 및 배포 파이프라인에 권한 확인을 통합해야 함**을 의미합니다.

429 오류에 대한 `Retry-After` 헤더는 [7, 22] 단순한 제안이 아니라 서버에서 지시하는 명령입니다. `Retry-After`가 존재할 때 이를 무시하거나 일반적인 백오프를 사용하는 것은 스로틀링을 악화시키고 서비스 가용성을 연장시킬 가능성이 높습니다. 이는 모듈의 재시도 로직이 **`Retry-After` 값을 우선시하고 엄격히 준수해야 함**을 의미하며, 이는 Graph API에서 "좋은 시민" 행동을 유지하고 모듈의 장기적인 운영 안정성을 보장하는 데 결정적입니다.

**표 3: 메일 요청에 대한 일반적인 Microsoft Graph API 오류 코드**

| 상태 코드 | 오류 코드 (예시) | 의미 | 초기 문제 해결 단계 | 출처 |
| :--- | :--- | :--- | :--- | :--- |
| `400` | `badRequest` | 요청 형식이 잘못되었거나 올바르지 않음. | 요청 형식, 매개변수, 구문 수정. | [7, 20] |
| `401` | `unauthorized` | 호출자가 인증되지 않음; 토큰 누락/만료. | 새 접근 토큰 획득; 토큰 유효성 확인. | [7, 20] |
| `403` | `forbidden` | 권한 부족 또는 동의 누락. | Azure AD에 필요한 권한 추가; 필요한 경우 관리자 승인 확인. | [7, 20] |
| `404` | `notFound` | 리소스를 찾을 수 없음. | API 엔드포인트 URL 및 리소스 ID 확인. | [7, 20] |
| `429` | `tooManyRequests` | 앱/사용자가 스로틀링됨. | `Retry-After` 헤더를 사용한 재시도 로직 구현; 요청 빈도 감소. | [7, 20, 22] |
| `500` | `internalServerError` | 내부 서버 오류. | 기다린 후 요청 재시도. | [7, 20] |
| `503` | `serviceUnavailable` | 서비스가 일시적으로 사용 불가능. | 서비스 상태 확인; 새 HTTP 연결로 나중에 다시 시도. | [7, 20] |
| `504` | `gatewayTimeout` | 서버가 업스트림에서 적시에 응답을 받지 못함. | 백오프를 통한 재시도; `$search`와 같은 무거운 작업 피하기 (해당하는 경우). | [7, 20] |

-----

## 7\. 스로틀링 및 성능 최적화 모범 사례

Microsoft Graph는 서비스 가용성 및 신뢰성을 보장하기 위해 스로틀링 제한을 구현하며, 이는 시나리오에 따라 다릅니다(예: 쓰기 작업은 읽기보다 더 심하게 스로틀링됨).[22] 임계값을 초과하면 Microsoft Graph는 해당 클라이언트 앱의 추가 요청을 일정 시간 동안 제한하고, `HTTP 429 Too Many Requests` 상태 코드를 반환하며, 실패한 요청의 응답 헤더에 제안된 대기 시간을 포함하는 `Retry-After` 헤더를 반환합니다.[22] 스로틀링의 일반적인 원인으로는 테넌트의 모든 애플리케이션에 걸쳐 많은 수의 요청이 발생하거나, 특정 애플리케이션에서 모든 테넌트에 걸쳐 많은 수의 요청이 발생하는 경우가 있습니다.[22] 전반적으로 Microsoft Graph는 초당 2,000개의 요청으로 제한됩니다.[7]

### 스로틀링 방지 전략

  * **요청당 작업 수 줄이기:** `$select`를 사용하여 필요한 데이터만 가져오도록 쿼리를 최적화합니다.[7, 22]
  * **호출 빈도 줄이기:** 요청 간 간격을 두어 제한 내에 머무르도록 합니다.[7, 21, 22] 지속적인 폴링이나 컬렉션의 정기적인 스캔은 피해야 합니다.[22]
  * **`Retry-After`를 사용한 재시도 로직 구현:** 섹션 6에서 자세히 설명했듯이, `Retry-After` 헤더를 준수하고 제공되지 않을 경우 지수 백오프를 사용합니다.[22]
  * **응답 캐싱:** 가능한 경우 응답을 캐싱하여 중복 API 호출을 최소화합니다.[7]
  * **더 작고 집중된 요청:** 한 번에 너무 많은 데이터를 가져오는 것을 피합니다.[7]

### 요청 일괄 처리 및 사서함당 제한 고려 사항

JSON 일괄 처리는 여러 요청을 단일 HTTP 호출로 결합하여 애플리케이션 성능을 최적화할 수 있습니다.[22] 그러나 일괄 처리 내의 요청은 스로틀링 제한에 대해 개별적으로 평가됩니다. 일괄 처리 내의 요청 중 하나라도 `429`로 실패하면, 일괄 처리 자체는 `200 OK`로 성공하지만, 개별 실패 요청 세부 정보( `Retry-After` 포함)는 일괄 처리 응답에 포함됩니다.[22] Exchange 관련 작업(메일, 캘린더, 연락처)에는 특정 일괄 처리 제한이 있습니다: 최대 20개의 요청을 일괄 처리할 수 있지만, 단일 일괄 처리 내에서는 *사서함당 4개의 요청만* 결합할 수 있습니다.[21] 이는 여러 사서함을 처리하는 애플리케이션의 경우 고급 큐잉이 필요함을 의미합니다.[21]

일괄 처리가 API 호출 수를 줄여 스로틀링을 피하는 방법처럼 보일 수 있지만, 문서에서는 "일괄 처리 내의 요청은 스로틀링 제한에 대해 개별적으로 평가된다"고 명확히 밝히고 있으며 [22], Exchange 작업의 경우 사서함당 4개의 요청이라는 상당히 제한적인 일괄 처리 한계를 가지고 있습니다.[21] 이는 일괄 처리가 주로 네트워크 최적화(HTTP 왕복 횟수 감소)이지, 스로틀링을 직접적으로 회피하는 메커니즘이 아님을 의미합니다. 모듈은 일괄 처리를 통해 마법처럼 속도 제한을 우회하려고 시도해서는 안 되며, **기존 스로틀링 제약 조건 *내에서* 효율성을 향상시키는 데 사용해야 합니다.**

### 대량 추출을 위한 Microsoft Graph Data Connect 고려 시점

Microsoft Graph REST API 스로틀링 제한을 받지 않고 Microsoft Graph에서 *대량의 데이터*를 추출해야 하는 솔루션의 경우, **Microsoft Graph Data Connect가 권장되는 솔루션입니다.**[22] 이는 대량 데이터 추출 시나리오를 위한 대안입니다.

"대량의 데이터" 추출을 위해 Microsoft Graph Data Connect를 사용하도록 명시적으로 권장하는 것은 [22] 중요한 아키텍처적 신호입니다. 이는 표준 REST API가 모범 사례를 따르더라도 대량 데이터 작업에 대한 본질적인 확장성 한계를 가지고 있음을 의미합니다. 방대한 과거 데이터를 처리하거나 대규모 분석을 수행해야 하는 엔터프라이즈 수준의 메일 쿼리 모듈의 경우, REST API에만 의존하면 필연적으로 스로틀링 문제가 발생할 것입니다. 이는 모듈 설계 시 **Data Connect를 대량 작업을 위한 별도의 전문 구성 요소로 고려해야 하며,** 이러한 사용 사례를 트랜잭션 REST API를 통해 강제하려고 시도해서는 안 됨을 시사합니다. 이는 확장성을 위한 근본적인 아키텍처적 결정입니다.

-----

## 8\. 결론 및 추가 자료

메일 쿼리 모듈의 성공적인 구현은 Microsoft Graph API의 인증, 핵심 엔드포인트, 그리고 고급 쿼리 기능에 대한 깊은 이해에 달려 있습니다. 보안과 지속적인 운영을 위해 **최소 권한 원칙과 견고한 토큰 관리를 우선시해야 합니다.** OData 쿼리 매개변수(`$filter`, `$select`, `$orderby`)를 활용하여 정확한 데이터 검색과 성능 최적화를 달성하되, 특정 규칙과 제한 사항을 유념해야 합니다. `@odata.nextLink` 및 `$skiptoken`을 사용하여 대규모 데이터셋을 효과적으로 처리하기 위한 **탄력적인 페이지 매김 로직을 구현해야 합니다.** `Retry-After` 헤더에 따라 지능적인 재시도 메커니즘을 포함한 포괄적인 오류 처리를 통합하는 것이 중요합니다. 마지막으로, 요청 빈도 감소, 더 작은 요청, 그리고 대량 작업 시 Microsoft Graph Data Connect 고려와 같은 전략을 사용하여 스로틀링 제한을 염두에 두고 모듈을 설계해야 합니다.

Graph Explorer(`aka.ms/ge`)의 반복적인 언급과 [2, 3, 7] SDK를 정기적으로 업데이트하라는 권장 사항은 [7] 단순한 편의성을 넘어 빠르게 진화하는 API와 보조를 맞추는 것의 중요성을 나타냅니다. 이는 성공적인 모듈 개발이 일회성 노력이 아니라, 테스트, 디버깅, 새로운 기능 또는 수정 사항 채택을 위해 제공된 도구를 활용하면서 Graph 생태계에 지속적으로 참여해야 함을 의미합니다.

보고서의 구조가 인증부터 쿼리, 페이지 매김, 오류 처리, 스로틀링으로 이어지는 방식은 이러한 요소들이 고립된 문제가 아님을 강조합니다. 예를 들어, 부실한 페이지 매김(섹션 5)은 스로틀링(섹션 7)으로 이어질 수 있으며, 이는 다시 특정 오류 처리(섹션 6)를 요구합니다. 마찬가지로, 비효율적인 필터링(섹션 4)은 페이로드 크기를 증가시켜 성능에 영향을 미치고 잠재적으로 스로틀링에 기여할 수 있습니다. 이는 모듈의 성공이 **각 모범 사례가 다른 모범 사례를 강화하는 전체론적 접근 방식에 달려 있음**을 의미하며, 이는 견고하고 성능이 뛰어나며 유지보수 가능한 시스템으로 이어집니다. 한 영역의 실패는 다른 영역에 연쇄적인 영향을 미칠 수 있으므로, 통합된 설계의 필요성이 강조됩니다.

### 공식 Microsoft Graph 문서 및 도구 링크

  * **Microsoft Graph 문서 홈:** [https://learn.microsoft.com/en-us/graph/](https://learn.microsoft.com/en-us/graph/) [2]
  * **Microsoft Graph Explorer:** `aka.ms/ge` [2, 3, 7] - API 호출 테스트, 권한 이해 및 응답 미리 보기를 위한 매우 유용한 도구.
  * **Microsoft Graph 데이터 페이지 매김:** [https://learn.microsoft.com/en-us/graph/paging](https://learn.microsoft.com/en-us/graph/paging) [18]
  * **스로틀링 지침:** [https://learn.microsoft.com/en-us/graph/throttling](https://learn.microsoft.com/en-us/graph/throttling) [22]
  * **메시지 리소스 유형 속성:** [https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0) [8, 10]
  * **필터링 쿼리 매개변수:** [https://learn.microsoft.com/en-us/graph/filter-query-parameter](https://learn.microsoft.com/en-us/graph/filter-query-parameter) [12]
  * **검색 쿼리 매개변수:** [https://learn.microsoft.com/en-us/graph/search-query-parameter](https://learn.microsoft.com/en-us/graph/search-query-parameter) [16]
  * **오류 응답 및 리소스 유형:** [https://learn.microsoft.com/en-us/graph/workbook-error-codes](https://learn.microsoft.com/en-us/graph/workbook-error-codes) [20] - (참고: 이 특정 링크는 통합 문서용이지만, Graph API의 일반적인 오류 처리 개념을 가리킵니다.) 일반적인 오류 처리 팁: [https://nboldapp.com/handling-microsoft-graph-api-errors-tips-and-tricks/](https://nboldapp.com/handling-microsoft-graph-api-errors-tips-and-tricks/) [7]

-----

이 명세서가 Microsoft Graph API를 활용한 메일 쿼리 모듈 구현에 도움이 되기를 바랍니다. 추가적으로 궁금한 점이 있으신가요?