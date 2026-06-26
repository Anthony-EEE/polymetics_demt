# DEMT Polymetis HPC 安装与无头采集指南

本文档面向在 HPC/Slurm 计算节点上安装 `Anthony-EEE/polymetics_demt`，并用 PyBullet `DIRECT` 模式无界面采集 DEMT 原始数据。

当前推荐分支：

```bash
hpc-headless-data-collection
```

## 1. 准备登录节点环境

按 HPC 实际情况加载 Anaconda/Miniconda。常见形式如下，二选一即可：

```bash
module load anaconda
```

或：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
```

建议把仓库放到有足够空间的项目盘或 scratch 盘，不要把大规模数据写到 home。

```bash
mkdir -p /path/to/project
cd /path/to/project
```

## 2. 克隆 DEMT 版本 Polymetis

```bash
git clone https://github.com/Anthony-EEE/polymetics_demt.git
cd polymetics_demt
git checkout hpc-headless-data-collection
```

确认分支：

```bash
git status -sb
```

应看到类似：

```text
## hpc-headless-data-collection...origin/hpc-headless-data-collection
```

## 3. 创建 Conda 环境

推荐先用上游 Polymetis 的环境文件创建 Python 3.8 环境：

```bash
conda env create -f polymetis/environment.yml
conda activate polymetis-local
```

如果 HPC 上解析 `environment.yml` 很慢或某些旧包不可用，可以使用最小运行环境：

```bash
conda create -n polymetis38 python=3.8 -y
conda activate polymetis38
conda install -c fair-robotics -c conda-forge polymetis pybullet numpy scipy pandas tqdm -y
```

DEMT 数据采集保存 `.ply` 点云时还需要 `open3d`：

```bash
conda install -c open3d-admin -c conda-forge open3d -y
```

如果该 channel 在 HPC 上不可用，尝试：

```bash
pip install open3d
```

## 4. 安装本仓库 Python 包

从仓库根目录执行：

```bash
pip install -e ./polymetis
```

检查核心依赖：

```bash
python - <<'PY'
import numpy
import pybullet
import open3d
print("numpy", numpy.__version__)
print("pybullet ok")
print("open3d", open3d.__version__)
PY
```

## 5. 语法检查

```bash
python -m py_compile \
  examples/collection_io.py \
  examples/main.py \
  examples/main_insert.py
```

## 6. HPC 无头采集规则

HPC 上必须遵守：

- 一定要传 `--no-gui`，否则 PyBullet 会尝试打开 GUI。
- 一定要传 `--output-dir`，否则脚本会进入本地预览循环。
- 不要传 `--preview`。
- 输出目录建议放在 scratch/project 存储，例如 `$SCRATCH/demt_raw/...`。
- `--num-demos` 表示最终保留的成功 demo 数；失败 demo 会被删除并重试。
- `--max-collection-attempts 0` 表示使用默认上限 `max(num_demos * 10, num_demos + 10)`。

## 7. Cube grasp-lift 采集

小规模 smoke test：

```bash
python examples/main.py \
  --output-dir /tmp/demt_hpc_cube_check \
  --num-demos 1 \
  --seed 11 \
  --sample-hz 1 \
  --no-gui \
  --max-collection-attempts 2
```

正式采集示例：

```bash
python examples/main.py \
  --output-dir /path/to/scratch/demt_raw/cube_grasp_lift \
  --num-demos 100 \
  --seed 1 \
  --sample-hz 30 \
  --no-gui \
  --success-lift-height 0.20 \
  --max-collection-attempts 0
```

带 approaching-region 的采集示例：

```bash
python examples/main.py \
  --output-dir /path/to/scratch/demt_raw/cube_grasp_lift_approach_xz_grid \
  --num-demos 100 \
  --seed 7 \
  --sample-hz 30 \
  --no-gui \
  --approach-noise-mode xz_grid \
  --approach-noise-radius 0.04 \
  --approach-grid-size 5 \
  --success-lift-height 0.20 \
  --max-collection-attempts 0
```

每个 `demo_<id>` 会写出 `metadata.json`，其中包含 `approach_region_label`、`approach_offset`、`pre_grasp` 和 `success` 信息。

## 8. Peg insertion 采集

推荐使用 `--start-with-peg`，即从 home 姿态开始，peg 已经被夹在 gripper 中，只采集 transport-to-hole 和 insertion 阶段。

小规模 smoke test：

```bash
python examples/main_insert.py \
  --start-with-peg \
  --output-dir /tmp/demt_hpc_insert_check \
  --num-demos 1 \
  --seed 12 \
  --sample-hz 1 \
  --no-gui \
  --max-collection-attempts 2
```

正式采集示例：

```bash
python examples/main_insert.py \
  --start-with-peg \
  --output-dir /path/to/scratch/demt_raw/peg_insert_home_held \
  --num-demos 100 \
  --seed 1 \
  --sample-hz 30 \
  --no-gui \
  --success-xy-tolerance 0.012 \
  --success-max-peg-center-z 0.12 \
  --success-min-vertical-dot 0.95 \
  --max-collection-attempts 0
```

## 9. Slurm 脚本模板

根据 HPC 配置调整 partition、time、mem、account 和 conda 路径：

```bash
#!/bin/bash
#SBATCH --job-name=demt_cube_collect
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate polymetis38

cd /path/to/project/polymetics_demt
mkdir -p logs

python examples/main.py \
  --output-dir "$SCRATCH/demt_raw/cube_grasp_lift" \
  --num-demos 100 \
  --seed 1 \
  --sample-hz 30 \
  --no-gui \
  --success-lift-height 0.20 \
  --max-collection-attempts 0
```

提交：

```bash
sbatch collect_cube.slurm
```

## 10. 输出结构

原始数据目录形如：

```text
raw_dataset_root/
  demo_0/
    metadata.json
    frame_0/
      point_cloud.ply
      arm_joints.txt
      hand_joints.txt
      ee_pose.txt
      time.txt
      commanded_speed.txt
      commanded_dt.txt
      phase.txt
      cube_pose.txt 或 peg_pose.txt
```

该结构保持兼容旧的 ARCap HDF5 builder。

## 11. 转 HDF5

如果 HPC 上另有 ARCap 环境，建议在那个环境里转换：

```bash
conda activate arcap
python -c "import sys; sys.path.insert(0, 'ARcap_train/STEP1_build_dataset'); from dataset_utils import process_hdf5_arcap_multi; process_hdf5_arcap_multi('/path/to/output.hdf5', ['/path/to/raw_dataset_root'], 2, 10000, hand_ahead=0, last_mean=5)"
```

注意：旧 HDF5 builder 会忽略 `metadata.json`。如果实验需要按 approaching region 分组，建议先为不同 region/sampling mode 生成不同 raw/HDF5 数据集，或后续扩展 HDF5 builder 把 demo-level metadata 写入 attrs/mask。

## 12. 常见问题

### 运行时卡住不退出

通常是漏了 `--output-dir`，脚本进入了本地预览循环。HPC 上同时传：

```bash
--no-gui --output-dir /path/to/output
```

并且不要传 `--preview`。

### `ModuleNotFoundError: No module named 'open3d'`

安装：

```bash
conda install -c open3d-admin -c conda-forge open3d -y
```

或：

```bash
pip install open3d
```

### PyBullet 尝试打开窗口或报显示错误

确认命令包含：

```bash
--no-gui
```

脚本在该模式下会使用 `pb.DIRECT`。

### 成功 demo 数不够

失败 demo 会被删除并重试。可以放宽 success threshold 或增加尝试上限：

```bash
--max-collection-attempts 500
```

### 不建议在登录节点跑大规模采集

登录节点只适合 smoke test。正式采集请通过 Slurm 提交到计算节点。
