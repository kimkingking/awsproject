import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 50, 
  duration: '1m',
};

export default function () {
  // 워커 노드의 '퍼블릭 IP'를 사용해야 합니다!
  const target_url = 'https://www.pluseticket.store'; 
  http.get(target_url);
  sleep(0.1);
}