# NoC 합성 최적화 방법론 (NoC Synthesis Optimization Methodology)

## 목차
1. [개요](#개요)
2. [NoC 합성 방식](#noc-합성-방식)
3. [비용 함수 (Cost Functions)](#비용-함수-cost-functions)
4. [최적화 알고리즘](#최적화-알고리즘)
5. [설계 공간 탐색](#설계-공간-탐색)
6. [성능 평가 지표](#성능-평가-지표)

---

## 개요

PyMTL3-net은 **파라미터화된 구성 기반 NoC 생성 프레임워크**로, 사용자가 지정한 설정에 따라 합성 가능한 Verilog를 생성합니다.

### 핵심 특징
- **다층 모델링**: FL (Functional Level), CL (Cycle Level), RTL (Register Transfer Level)
- **구성 기반 합성**: YAML 설정 파일 또는 CLI를 통한 파라미터 제어
- **자동화된 특성 분석**: EDA 툴플로우를 통한 면적, 에너지, 타이밍 분석

---

## NoC 합성 방식

### 1. 파라미터화된 컴포넌트 생성

NoC는 **구성 파라미터에 따라 동적으로 인스턴스화**되는 방식으로 합성됩니다.

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:121-135

def _mk_mesh_net( opts ):
  ncols  = opts.ncols
  nrows  = opts.nrows
  nports = opts.ncols * opts.nrows
  payload_nbits = opts.channel_bw
  channel_lat   = opts.channel_lat

  Pos = mk_mesh_pos( ncols, nrows )
  Pkt = mk_mesh_pkt( ncols, nrows, vc=1, payload_nbits=payload_nbits )

  if hasattr( opts, 'cl' ) and opts.cl:
    cl_net = MeshNetworkCL( Pkt, Pos, ncols, nrows, channel_lat )
    net    = CLNetWrapper( Pkt, cl_net, nports )
  else:
    net = MeshNetworkRTL( Pkt, Pos, ncols, nrows, channel_lat )
  return net
```

### 2. 지원되는 토폴로지

| 토폴로지 | 설명 | 파라미터 | 파일 위치 |
|---------|------|---------|----------|
| **Ring** | 선형 링 인터커넥트 | `nterminals`, `channel_lat` | `ringnet/RingNetworkRTL.py` |
| **Mesh** | 2D 그리드 네트워크 | `ncols`, `nrows`, `channel_lat` | `meshnet/MeshNetworkRTL.py` |
| **Torus** | 랩어라운드 2D 그리드 | `ncols`, `nrows`, `channel_lat` | `torusnet/TorusNetworkRTL.py` |
| **Concentrated Mesh** | 라우터당 다중 터미널 | `ncols`, `nrows`, `nterminals_each` | `cmeshnet/CMeshNetworkRTL.py` |
| **Butterfly** | k-ary n-fly 다단 네트워크 | `kary`, `nfly`, `channel_lat` | `bflynet/BflyNetworkRTL.py` |

### 3. Verilog 생성 프로세스

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:773-788

def gen_verilog( topo, opts ):
  os.system(f'[ ! -e {topo}.sv ] || rm {topo}.sv')

  # 네트워크 인스턴스 생성
  net = mk_net_inst( topo, opts )

  # Elaboration
  net.elaborate()

  # Verilog 변환 패스 적용
  net.set_metadata( VerilogTranslationPass.enable, True )
  net.set_metadata( VerilogTranslationPass.explicit_module_name, topo )
  net.apply( VerilogTranslationPass() )

  # 생성된 Verilog 파일 이동
  translated_top_module = net.get_metadata( VerilogTranslationPass.translated_top_module )
  os.system(f'mv {translated_top_module}__pickled.v {topo}.v')
```

### 4. 라우팅 알고리즘

#### DOR (Dimension Order Routing) - Y-then-X

```python
# 위치: pymtl3_net/meshnet/DORYMeshRouteUnitRTL.py:38-60

@update
def up_ru_routing():
  s.out_dir @= Bits3(0)
  for i in range( num_outports ):
    s.send[i].val @= Bits1(0)

  if s.recv.val:
    # 목적지 도달 시
    if (s.pos.pos_x == s.recv.msg.dst_x) & (s.pos.pos_y == s.recv.msg.dst_y):
      s.out_dir @= SELF
    # Y 차원 먼저 라우팅
    elif s.recv.msg.dst_y < s.pos.pos_y:
      s.out_dir @= SOUTH
    elif s.recv.msg.dst_y > s.pos.pos_y:
      s.out_dir @= NORTH
    # 그 다음 X 차원 라우팅
    elif s.recv.msg.dst_x < s.pos.pos_x:
      s.out_dir @= WEST
    else:
      s.out_dir @= EAST
    s.send[ s.out_dir ].val @= Bits1(1)
```

**특징**:
- **결정적(Deterministic)**: 같은 소스-목적지 쌍은 항상 같은 경로
- **데드락 프리(Deadlock-free)**: 순환 의존성 없음
- **최소 경로(Minimal)**: 최단 거리 경로 보장

---

## 비용 함수 (Cost Functions)

### 1. 주요 비용 메트릭: 평균 레이턴시

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:530-550

# 패킷 수신 시
if net.send[i].val:
  total_received += 1
  if int(net.send[i].msg.payload) > 0:
    timestamp = int(net.send[i].msg.payload)
    total_latency += ( ncycles - timestamp )  # 레이턴시 누적
    mpkt_received += 1

# 시뮬레이션 종료 시 평균 계산
if mpkt_received >= opts.measure_npackets:
  result.avg_latency = float( total_latency ) / mpkt_received
```

**레이턴시 계산 공식**:
```
평균_레이턴시 = Σ(수신_사이클 - 송신_사이클) / 측정_패킷_수
```

### 2. 보조 비용 메트릭

#### Zero-Load Latency (무부하 레이턴시)
```python
# 위치: examples/main.py:419, 439-440

if inj == 0:
  zero_load_lat = avg_lat
```

네트워크가 비어있을 때의 최소 레이턴시로, **홉 수와 채널 레이턴시**에 의해 결정됩니다.

#### Saturation Point (포화점)
```python
# 위치: examples/main.py:419

while inj < 100 and avg_lat <= 100 and avg_lat <= 2.5 * zero_load_lat:
```

**포화점 정의**: `평균_레이턴시 > 2.5 × 무부하_레이턴시`

이 시점에서 네트워크가 **대역폭 한계**에 도달했다고 판단합니다.

### 3. 3차 비용 메트릭 (EDA 툴플로우)

PyOCN은 [mflowgen](https://github.com/cornell-brg/mflowgen)을 통해 다음을 측정합니다:

- **면적 (Area)**: 표준 셀 기반 합성 면적 (μm²)
- **전력 (Power)**: 동적 + 정적 전력 (mW)
- **에너지 (Energy)**: 패킷당 에너지 소비 (pJ/packet)
- **타이밍 (Timing)**: 최대 주파수, 크리티컬 패스

---

## 최적화 알고리즘

### 1. 적응적 스윕 기반 탐색 (Adaptive Sweep-Based Exploration)

#### 알고리즘 개요

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:710-767

def net_simulate_sweep( topo, opts ):
  result_lst = []

  cur_inj       = 0      # 현재 주입률
  pre_inj       = 0      # 이전 주입률
  cur_avg_lat   = 0.0    # 현재 평균 레이턴시
  pre_avg_lat   = 0.0    # 이전 평균 레이턴시
  zero_load_lat = 0.0    # 무부하 레이턴시
  slope         = 0.0    # 레이턴시 증가율
  step          = opts.sweep_step  # 주입률 증가 스텝 (기본값: 10)
  threshold     = opts.sweep_thresh  # 레이턴시 임계값 (기본값: 100.0)

  while cur_avg_lat <= threshold and cur_inj <= 100:
    # 현재 주입률로 시뮬레이션 실행
    new_opts = deepcopy( opts )
    new_opts.injection_rate = max( 1, cur_inj )
    result = sim_func( topo, new_opts )
    result_lst.append( result )

    cur_avg_lat = result.avg_latency

    # 무부하 레이턴시 저장
    if cur_inj == 0:
      zero_load_lat = cur_avg_lat

    # 적응적 스텝 조정
    else:
      slope = ( cur_avg_lat - pre_avg_lat ) / ( cur_inj - pre_inj )
      if slope >= 1.0:
        step = max( 1, step // 2 )  # 기울기가 가파르면 스텝 감소

    # 다음 주입률로 이동
    pre_inj =  cur_inj
    cur_inj += step
    pre_avg_lat = cur_avg_lat
```

#### 최적화 전략

**스텝 크기 적응 로직**:
```
if (dLatency / dInjection) >= 1.0:
    step = max(1, step // 2)
```

- **초기 단계**: 큰 스텝(10%)으로 빠르게 탐색
- **포화 근처**: 기울기가 가파르면 스텝을 절반으로 줄여 정밀 탐색
- **종료 조건**: `레이턴시 > 임계값` 또는 `주입률 > 100%`

### 2. 예시: 적응적 vs 고정 스텝

| 주입률 (%) | 평균 레이턴시 | 기울기 | 다음 스텝 크기 |
|-----------|-------------|-------|---------------|
| 0 | 5.2 | - | 10 (초기값) |
| 10 | 6.1 | 0.09 | 10 |
| 20 | 7.3 | 0.12 | 10 |
| 30 | 9.5 | 0.22 | 10 |
| 40 | 13.7 | 0.42 | 10 |
| 50 | 22.1 | 0.84 | 10 |
| 60 | 45.3 | **2.32** | **5** (절반) |
| 65 | 67.8 | **4.5** | **2** (절반) |
| 67 | 89.2 | **10.7** | **1** (절반) |
| 68 | 112.4 | - | 종료 (임계값 초과) |

**효율성**:
- 고정 스텝 (1%): 100회 시뮬레이션 필요
- 적응적 스텝: **~10회 시뮬레이션**으로 포화점 발견

---

## 설계 공간 탐색

### 1. 구성 파라미터

#### YAML 설정 파일 (config.yml)

```yaml
# 위치: examples/config.yml

# 토폴로지 파라미터
network         : 'Mesh'
terminal        : 16        # 터미널 수
dimension       : 4         # 행/열 수
channel_latency : 0         # 채널 레이턴시 (0 = 조합 논리)

# 실행할 작업
action:
  - generate              # Verilog 생성
  - verify                # 정확성 검증
  - simulate-1pkt         # 단일 패킷 시뮬레이션
  - simulate-lat-vs-bw    # 레이턴시-대역폭 특성 분석

# 트래픽 패턴
pattern:
  - urandom     # 균등 무작위
  - complement  # 비트 반전
  - partition   # 파티션
  - opposite    # 반대편
  - neighbor    # 이웃
```

#### CLI 인터페이스

```bash
# Verilog 생성
./pymtl3-net gen mesh --ncols 4 --nrows 4 --channel-lat 0

# 성능 특성 분석 (적응적 스윕)
./pymtl3-net sim mesh --ncols 4 --nrows 4 --sweep --pattern urandom

# 단일 시뮬레이션 (고정 주입률)
./pymtl3-net sim mesh --ncols 4 --nrows 4 --injection-rate 50
```

### 2. 탐색 가능한 설계 공간

| 차원 | 파라미터 | 값 범위 | 영향 |
|-----|---------|--------|-----|
| **토폴로지** | topology | Ring, Mesh, Torus, CMesh, Bfly | 네트워크 구조, 직경, 대역폭 |
| **크기** | ncols, nrows | 2-16 | 터미널 수, 면적, 전력 |
| **버퍼링** | channel_lat | 0-4 | 처리량 vs 레이턴시, 면적 |
| **대역폭** | channel_bw | 8-128 bits | 링크 대역폭, 배선 오버헤드 |
| **가상 채널** | vc | 1-4 | 데드락 방지, 처리량 향상 |

### 3. 설계 공간 탐색 예제

```python
# 위치: examples/main.py:419-452

# 동적 주입률 조정 (개선된 알고리즘)
inj_shamt_mult  = 5
inj_shamt       = 0.0
inj_step        = 10
running_avg_lat = 0.0

while inj < 100 and avg_lat <= 100 and avg_lat <= 2.5 * zero_load_lat:
  # 시뮬레이션 실행
  results = simulate_lat_vs_bw(...)
  avg_lat = results[0]

  if inj == 0:
    zero_load_lat = avg_lat

  # 이동 평균 기반 적응적 스텝 조정
  if running_avg_lat == 0.0:
    running_avg_lat = int(avg_lat)
  else:
    running_avg_lat = 0.5 * int(avg_lat) + 0.5 * int(running_avg_lat)

  # 지수적 스텝 감소
  inj_shamt = ( (int(avg_lat) / running_avg_lat) - 1 ) * inj_shamt_mult
  inj_step  = inj_step >> int(inj_shamt)  # 비트 시프트로 절반씩 감소
  if inj_step < 1:
    inj_step = 1
  inj += inj_step
```

**개선점**:
- **이동 평균**: 노이즈에 강건한 기울기 추정
- **지수적 감소**: 급격한 레이턴시 증가 구간에서 세밀한 탐색
- **조기 종료**: 2.5× 무부하 레이턴시 초과 시 중단

---

## 성능 평가 지표

### 1. 시뮬레이션 결과 출력

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:413-434

@dataclass
class SimResult:
  injection_rate : int   = 0    # 주입률 (%)
  avg_latency    : float = 0.0  # 평균 레이턴시 (사이클)
  pkt_generated  : int   = 0    # 생성된 패킷 수
  mpkt_received  : int   = 0    # 측정용 패킷 수신 수
  total_received : int   = 0    # 총 수신 패킷 수
  sim_ncycles    : int   = 0    # 시뮬레이션 사이클 수
  elapsed_time   : float = 0.0  # 실제 시뮬레이션 시간 (초)
  timeout        : bool  = False # 타임아웃 여부

  def to_row( self ):
    return f'| {self.injection_rate:4} | {self.avg_latency:8.2f} | {self.sim_ncycles/self.elapsed_time:5.1f} |'
```

### 2. 출력 테이블 예시

```
+------+----------+-------+
| inj% | avg. lat | speed |
+------+----------+-------+
|    0 |     5.20 |  823.4|
|   10 |     6.10 |  812.1|
|   20 |     7.30 |  798.3|
|   30 |     9.50 |  776.5|
|   40 |    13.70 |  745.2|
|   50 |    22.10 |  687.9|
|   60 |    45.30 |  521.3|
|   65 |    67.80 |  398.7|
|   67 |    89.20 |  312.4|
|   68 |   112.40 |  256.1|
+------+----------+-------+
```

### 3. 핵심 성능 지표 추출

- **무부하 레이턴시**: 5.20 사이클
- **포화점**: ~67% 주입률 (레이턴시 = 89.2 > 2.5 × 5.20)
- **최대 대역폭**: ~0.67 packets/cycle/terminal
- **시뮬레이션 속도**: ~800 cycles/second (저부하), ~250 cycles/second (고부하)

### 4. 트래픽 패턴별 특성

```python
# 위치: pymtl3_net/ocnlib/sim/sim_utils.py:206-218

def _gen_dst_id( pattern, nports, src_id ):
  if pattern == 'urandom':
    return randint( 0, nports-1 )  # 균등 무작위
  elif pattern == 'partition':
    return randint( 0, nports-1 ) & ( nports//2 - 1 ) | ( src_id & ( nports//2 ) )  # 파티션 지역성
  elif pattern == 'opposite':
    return ( src_id + nports//2 ) % nports  # 반대편 (최대 거리)
  elif pattern == 'neighbor':
    return ( src_id + 1 ) % nports  # 이웃 (최소 거리)
  elif pattern == 'complement':
    return ( nports-1 ) - src_id  # 비트 반전
```

**패턴별 특성**:
- `urandom`: 평균 홉 거리, 고르게 분산된 부하
- `neighbor`: 최소 홉, 낮은 레이턴시, 링크 불균형
- `opposite`: 최대 홉, 높은 레이턴시
- `partition`: 지역성 있는 통신, 실제 워크로드 모델링

---

## 최적화 권장사항

### 1. 레이턴시 최적화
- **채널 레이턴시 0**: 조합 논리 경로로 홉당 1 사이클
- **짧은 직경 토폴로지**: Mesh보다 Torus 고려
- **DOR 라우팅**: 최소 경로 보장

### 2. 처리량 최적화
- **가상 채널 추가**: VC=2 이상으로 헤드-오브-라인 블로킹 완화
- **채널 대역폭 증가**: 32비트 → 64비트
- **파이프라인 채널**: channel_lat=1로 처리량 향상

### 3. 면적/전력 최적화
- **버퍼 최소화**: channel_lat=0 (버퍼 없음)
- **작은 VC 개수**: VC=1
- **집중형 토폴로지**: CMesh로 라우터 수 감소

### 4. 설계 공간 탐색 전략

```bash
# 1단계: 토폴로지별 포화점 비교
for topo in mesh torus ring; do
  ./pymtl3-net sim $topo --ncols 4 --nrows 4 --sweep --pattern urandom
done

# 2단계: 최적 토폴로지에서 크기 탐색
for size in 2 4 8; do
  ./pymtl3-net sim mesh --ncols $size --nrows $size --sweep --pattern urandom
done

# 3단계: 파이프라이닝 효과 분석
for lat in 0 1 2; do
  ./pymtl3-net sim mesh --ncols 4 --nrows 4 --channel-lat $lat --sweep
done

# 4단계: Verilog 생성 및 PPA 분석 (mflowgen 필요)
./pymtl3-net gen mesh --ncols 4 --nrows 4 --channel-lat 0
# mflowgen 툴플로우로 면적/전력/타이밍 추출
```

---

## 참고문헌

### 구현 파일 위치

| 기능 | 파일 경로 | 핵심 라인 |
|-----|----------|---------|
| Verilog 생성 | `pymtl3_net/ocnlib/sim/sim_utils.py` | 773-788 |
| 비용 계산 | `pymtl3_net/ocnlib/sim/sim_utils.py` | 530-550 |
| 적응적 스윕 | `pymtl3_net/ocnlib/sim/sim_utils.py` | 710-767 |
| DOR 라우팅 | `pymtl3_net/meshnet/DORYMeshRouteUnitRTL.py` | 38-60 |
| Mesh 네트워크 | `pymtl3_net/meshnet/MeshNetworkRTL.py` | 전체 |
| 설정 예제 | `examples/config.yml` | 전체 |
| CLI 진입점 | `script/pymtl3-net` | 전체 |

### 논문
- Cheng Tan et al., "PyOCN: A Unified Framework for Modeling, Testing, and Evaluating On-Chip Networks", ICCD 2019

### 관련 툴
- [mflowgen](https://github.com/cornell-brg/mflowgen): PPA 분석용 EDA 툴플로우 생성기
- [PyMTL3](https://github.com/pymtl/pymtl3): Python 기반 하드웨어 모델링 프레임워크

---

**작성일**: 2025-10-21
**버전**: 1.0
