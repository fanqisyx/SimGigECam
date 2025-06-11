# 模拟GigE相机的上位机软件需求文档

## 概述
本软件旨在在上位机（host computer）上模拟GigE相机，符合GigE Vision标准，用于工业视觉系统的开发、测试和调试。软件通过网络模拟真实GigE相机的行为，支持设备发现、控制命令处理和图像数据传输。以下是详细的软件需求，涵盖核心功能和可选特性。

## 功能需求

### 1. 网络通信
- **设备发现机制**：
  - 实现GigE Vision设备发现机制，允许上位机通过网络发现模拟相机。
  - 支持动态IP地址分配和相机识别。
- **GigE Vision控制协议（GVCP）**：
  - 处理来自上位机的控制和配置命令，例如设置分辨率、帧率、触发模式等。
  - 支持配置数据通道（stream channels）以传输图像和配置数据。
- **GigE Vision流协议（GVSP）**：
  - 将图像数据分包并通过UDP/IP传输至上位机。
  - 实现丢包检测和重传机制，确保数据完整性。
- **网络支持**：
  - 兼容1 Gbit和10 Gbit以太网设备。
  - 支持Wi-Fi传输（可选）。

### 2. 图像生成
- **图像来源**：
  - 支持以下图像来源：
    - 静态图像（BMP、JPEG、TIFF格式）。
    - 视频序列（AVI文件）。
    - 合成测试图案或数据。
  - 允许用户加载自定义图像或数据。
- **图像格式**：
  - 支持GenICam PFNC定义的像素格式，包括单色和彩色图像。
  - 支持3D点云格式（可选）。
- **图像压缩**：
  - 提供JPEG和H.264编码器（可选）。
  - 支持自动帧压缩以优化网络带宽。

### 3. 配置与控制
- **相机参数**：
  - 支持配置以下参数：
    - 分辨率（宽度和高度）。
    - 帧率。
    - 像素格式。
    - 曝光时间、增益（可选）。
  - 参数通过GVCP命令可控。
- **触发模式**：
  - 支持软件触发模式，响应触发命令发送图像。
  - 支持硬件触发模拟（可选）。
- **GenICam兼容性**：
  - 使用GenICam标准生成XML设备描述文件，描述相机功能。
  - 支持GenICam特征控制接口。

### 4. 同步与多相机支持
- **精确时间协议（PTP）**：
  - 支持IEEE-1588 PTP，用于多相机同步（可选）。
- **多虚拟相机**：
  - 允许在单主机上模拟多个虚拟相机。
  - 每台虚拟相机具有独立IP/MAC地址。

### 5. 错误处理与网络模拟
- **错误处理**：
  - 实现GigE Vision标准的丢包重传机制。
  - 处理网络中断和超时。
- **网络条件模拟**：
  - 支持模拟包乱序、丢包等网络状况，用于测试上位机软件鲁棒性（可选）。

### 6. 用户界面
- **界面功能**：
  - 提供图形用户界面（GUI）或命令行界面，用于：
    - 启动/停止模拟。
    - 配置相机参数和网络设置。
    - 实时监控网络流量和相机状态。
- **日志记录**：
  - 记录所有交互、命令和错误信息，便于调试。

### 7. 性能与优化
- **性能优化**：
  - 支持多核处理器和SSE指令优化。
  - 实现防火墙穿透和包大小协商。
- **访问模式**：
  - 支持独占访问和带切换的控制访问。

### 8. 附加功能（可选）
- **图像格式转换**：
  - 支持RGB到Bayer原始格式转换。
  - 支持16位到10/12位压缩格式转换。
- **线扫描相机模拟**：
  - 支持线扫描（Linescan）相机模式。
- **接口转换**：
  - 支持将模拟、USB、CameraLink等接口转换为虚拟GigE相机。
- **分流视频**：
  - 支持将视频分成多个数据流通道。

## 非功能需求

### 1. 标准与兼容性
- **GigE Vision标准**：
  - 遵守GigE Vision 2.0或更高版本规范。
  - 参考[GigE Vision Specification](https://www.visiononline.org/userAssets/aiaUploads/File/GigE_Vision_Specification_2-0-03.pdf)。
- **GenICam标准**：
  - 使用GenICam描述相机特征，参考[GenICam Standard](http://www.genicam.org/)。
- **兼容性**：
  - 与主流GigE Vision客户端软件和硬件接收器兼容。

### 2. 平台支持
- 支持Windows和Linux（x86、ARM）操作系统。
- 推荐使用C#、Python或C++开发。

### 3. 性能要求
- 低延迟传输（目标延迟≤75ms）。
- 支持高带宽图像传输（最高125 MB/s）。

## 开发建议
- **参考实现**：
  - 参考开源项目[GigE-Cam-Simulator](https://github.com/tomsoftware/GigE-Cam-Simulator)，了解基本实现逻辑。
  - 该项目使用C#实现，支持设备发现和软件触发。
- **开发步骤**：
  1. 实现网络通信模块（GVCP、GVSP、设备发现）。
  2. 开发图像生成和处理模块。
  3. 集成GenICam XML文件生成。
  4. 设计用户界面和日志系统。
  5. 测试与主流GigE Vision客户端的兼容性。

## 文档与支持
- **用户文档**：
  - 提供安装、配置和使用指南。
  - 包含API文档（如果提供API）。
- **示例代码**：
  - 提供配置和运行示例。
- **技术支持**：
  - 提供常见问题解答和调试指南。

## 参考资源
| 资源名称 | 描述 | 链接 |
|----------|------|------|
| GigE Vision Specification | GigE Vision 2.0标准规范 | [GigE Vision Specification](https://www.visiononline.org/userAssets/aiaUploads/File/GigE_Vision_Specification_2-0-03.pdf) |
| GenICam Standard | GenICam标准官网 | [GenICam Standard](http://www.genicam.org/) |
| GigE-Cam-Simulator | 开源GigE相机模拟器 | [GigE-Cam-Simulator](https://github.com/tomsoftware/GigE-Cam-Simulator) |