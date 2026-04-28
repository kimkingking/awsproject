import http from 'k6/http';

export const options = {
  // 터미널 명령어 옵션을 따릅니다.
};

export default function () {
  // Ingress가 백엔드로 라우팅하는 기본 경로(/api/)에 무작위 난수를 붙여 
  // 백엔드 파드가 매번 강제로 연산(404 에러 생성)을 하도록 만듭니다.
  const target_url = `https://www.pluseticket.store/api/force-cpu-load?rand=${Math.random()}`;

  const params = {
    headers: {
      'X-Load-Test-Token': 'pluse-secret-pass', // WAF 무사 통과 암호
    },
  };

  // 요청 전송 (결과를 기다리지 않고 무자비하게 쏩니다)
  http.get(target_url, params);
  
  // ⭐️ 원래 있던 sleep(0.1)을 삭제했습니다. 
  // 이로 인해 요청 속도(RPS)가 수천 건 이상으로 폭발하여 파드의 CPU를 강제로 태웁니다.
}
