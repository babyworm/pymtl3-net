# NoC Topology Examples

30개의 현실적인 Network-on-Chip (NoC) 토폴로지 예제 모음입니다.

## 디렉토리 구조

```
examples/
├── small/      # 10개 예제: Initiators 8개, Targets 3개
├── medium/     # 10개 예제: Initiators <20개, Targets <20개
├── large/      # 10개 예제: 총 NIU <200개
└── README.md
```

## 설계 제약사항

- **Arbiter**: 최대 4:1 (4 입력 → 1 출력)
- **Decoder**: 최대 1:4 (1 입력 → 4 출력)
- **Node Types**: Initiator, Target, NIU, Router, Arbiter, Decoder, WidthConverter, ClockConverter

## Small-Scale Examples (Initiators 8개, Targets 3개)

| 파일 | 용도 | 총 노드 수 | 설명 |
|------|------|-----------|------|
| `mobile_soc.yml` | 모바일 SoC | 29 | 스마트폰 AP (CPU, GPU, ISP, NPU) |
| `iot_device.yml` | IoT 허브 | 24 | 스마트홈 (WiFi, BLE, 센서) |
| `automotive_adas.yml` | ADAS | 25 | 첨단 운전자 보조 (카메라, 레이더, 라이다) |
| `smart_camera.yml` | 보안 카메라 | 22 | AI 기반 H.265 인코딩 |
| `wearable.yml` | 스마트워치 | 22 | 저전력 건강 모니터링 |
| `home_assistant.yml` | 스마트 스피커 | 23 | 음성 제어 홈 허브 (WiFi6) |
| `drone_controller.yml` | 드론 | 24 | 비행 제어기 (4K 카메라) |
| `gaming_console.yml` | 게임 콘솔 | 25 | 휴대용 게임기 (GPU, 멀티미디어) |
| `network_switch.yml` | 네트워크 스위치 | 23 | 8포트 관리형 스위치 (QoS) |
| `medical_device.yml` | 의료 기기 | 23 | 환자 모니터링 (실시간 처리) |

**공통 특성**:
- Initiators: 8개
- Targets: 3개  
- NIUs: 8-11개
- Routers: 2-4개
- Clock Domains: 2-3개
- Data Width: 16-128 bits

## Medium-Scale Examples (Initiators <20개, Targets <20개)

| 파일 | Initiators | Targets | 총 노드 수 | 설명 |
|------|-----------|---------|-----------|------|
| `server_soc.yml` | 16 | 8 | 64 | 고성능 서버 (CPU, GPU, AI, PCIe Gen5) |
| `datacenter_nic.yml` | 14 | 6 | 48 | 100G 데이터센터 NIC (RDMA) |
| `automotive_cockpit.yml` | 15 | 10 | 57 | 디지털 콕핏 (멀티 디스플레이) |
| `5g_baseband.yml` | 18 | 8 | 60 | 5G 물리계층 (Massive MIMO) |
| `video_conferencing.yml` | 12 | 7 | 45 | 멀티 스트림 화상회의 |
| `industrial_controller.yml` | 14 | 9 | 53 | 산업용 PLC (EtherCAT) |
| `media_server.yml` | 16 | 11 | 62 | 멀티채널 트랜스코딩 |
| `ai_accelerator.yml` | 18 | 12 | 68 | AI 추론 가속기 |
| `edge_gateway.yml` | 13 | 8 | 49 | IoT 엣지 게이트웨이 |
| `robotics_controller.yml` | 15 | 10 | 57 | 로봇 제어기 (비전, 센서) |

**공통 특성**:
- Initiators: 12-18개
- Targets: 6-12개
- NIUs: 15-25개
- Routers: 4-8개
- Arbiters: 2-4개 (최대 4:1)
- Decoders: 1-3개 (최대 1:4)
- Clock Domains: 3-6개
- Data Width: 16-512 bits

## Large-Scale Examples (총 NIU <200개)

| 파일 | 총 NIU | 설명 |
|------|--------|------|
| `datacenter_soc.yml` | 180 | 64코어 데이터센터 SoC |
| `network_processor.yml` | 160 | 400G 네트워크 프로세서 (32 엔진) |
| `gpu_compute.yml` | 170 | 대규모 GPU (128 CU) |
| `ai_training_chip.yml` | 190 | AI 학습 칩 (256 텐서 코어) |
| `switch_fabric.yml` | 150 | 64포트 스위치 ASIC |
| `autonomous_vehicle_soc.yml` | 140 | 완전 자율주행 SoC |
| `hpc_node.yml` | 175 | HPC 노드 프로세서 (96코어) |
| `telecom_basestation.yml` | 155 | 대규모 MIMO 기지국 |
| `ml_inference_cluster.yml` | 165 | ML 추론 클러스터 (128 엔진) |
| `storage_controller.yml` | 145 | 엔터프라이즈 NVMe 컨트롤러 |

**공통 특성**:
- Initiators: 30-80개
- Targets: 20-60개
- NIUs: 140-190개
- Routers: 12-30개 (mesh/torus)
- Arbiters: 10-25개
- Decoders: 8-20개
- Clock Domains: 5-10개
- Data Width: 32-1024 bits

## 사용 방법

### 예제 로드

```python
from irregnet.graph_parser import load_heterogeneous_graph_from_yaml, validate_heterogeneous_graph

# Graph 로드
G, config = load_heterogeneous_graph_from_yaml('examples/small/mobile_soc.yml')

# 검증
errors, warnings = validate_heterogeneous_graph(G, config)

if errors:
    print("❌ 검증 오류:")
    for err in errors:
        print(f"  - {err}")
else:
    print("✅ Graph 검증 통과!")
```

### QoS 요구사항 분석

```python
# Bandwidth allocation 확인
bandwidth_allocs = config['constraints']['bandwidth_allocation']

for alloc in bandwidth_allocs:
    init_name = G.nodes[alloc['initiator']]['name']
    tgt_name = G.nodes[alloc['target']]['name']
    bw = alloc['guaranteed_bw']
    lat = alloc['max_latency']
    print(f"{init_name} → {tgt_name}: {bw} GB/s, {lat} cycles")
```

### 시각화

```python
from irregnet.topology_builder import TopologyBuilder

topo = TopologyBuilder.from_yaml('examples/medium/server_soc.yml')
topo.visualize('server_topology.png')
```

## QoS 패턴

### 우선순위 레벨
- **0 (최고)**: 실시간 제어, 디스플레이, 중요 센서
- **1 (중간)**: 비디오, 오디오, GPU, 네트워크
- **2 (최저)**: 백그라운드 스토리지, 설정, 로깅

### 트래픽 패턴
- **streaming**: 지속적 데이터 플로우 (비디오, 오디오)
- **bursty**: 간헐적 고강도 (CPU, 네트워크)
- **uniform**: 일정한 속도 (센서, 제어)

### 일반적인 지연 요구사항 (사이클)
- **초고성능**: 5-15 (비행 제어, 알람)
- **실시간**: 15-30 (디스플레이, ECG, 사용자 입력)
- **인터랙티브**: 30-60 (GPU, 카메라, 오디오)
- **Best-effort**: 60-200 (스토리지, 네트워크, 로깅)

## 설계 패턴

### 계층적 라우팅
```
Initiators → NIUs → Arbiters → Routers → Decoders → Target NIUs → Targets
```

### Clock Domain Crossing
```
Fast Domain → ClockConverter → Slow Domain
```

### Width Conversion
```
128-bit GPU → WidthConverter → 512-bit HBM
```

### 다중 레벨 중재
```
4 CPU Cores → Arbiter (4:1) → Router → Arbiter (3:1) → Memory
```

## 검증 규칙

1. **NIU Entry Point**: 모든 initiator/target은 NIU를 통해 연결
2. **Width Matching**: WidthConverter 없이는 edge width 일치 필요
3. **Clock Domains**: ClockConverter를 통한 도메인 크로싱 필요
4. **Arbiter 입력 개수**: 실제 in-degree와 `num_inputs` 일치
5. **Decoder 출력 개수**: 실제 out-degree와 `num_outputs` 일치
6. **Bandwidth**: guaranteed_bw 합 ≤ target max_bandwidth
7. **Latency**: End-to-end latency ≤ initiator latency_requirement

## 커스터마이징

새로운 예제 생성:

1. **Initiators 정의**: 트래픽 생성기 (CPU, GPU 등)
2. **Targets 정의**: 메모리/스토리지 목적지
3. **NIUs 추가**: Initiator/Target 당 하나씩
4. **토폴로지 설계**: Router, Arbiter, Decoder 추가
5. **Converter 추가**: Width/Clock 불일치 처리
6. **Edge 연결**: 데이터 경로 정의
7. **제약사항 설정**: QoS 요구사항
8. **검증**: 검증 체크 실행

## 참고자료

- [NoC 합성 문서](../opt.md)
- [Heterogeneous 노드 타입](../opt.md#heterogeneous-nodes)
- [QoS 검증](../opt.md#qos-validation)

## 라이센스

이 예제들은 교육 및 연구 목적으로 제공됩니다.

---

**생성 일자**: 2025-10-22
**버전**: 1.0
**총 예제 수**: 30개 (Small: 10, Medium: 10, Large: 10)
