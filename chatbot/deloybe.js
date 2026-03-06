// 1. Tạo hoặc lấy Session ID (lưu trong localStorage để giữ phiên khi reload trang)
    // let sessionId = localStorage.getItem('chat_session_id');
    // if (!sessionId) {
    //     sessionId = 'sess_' + Math.random().toString(36).substr(2, 9);
    //     localStorage.setItem('chat_session_id', sessionId);
    // }

// 2. Hàm gửi tin nhắn
    // async function sendMessageToBot(userMessage) {
    //     const backendUrl = 'http://localhost:8000/api/v1/chat'; // Thay đổi nếu deploy lên server thật

    //     try {
    //         const response = await fetch(backendUrl, {
    //             method: 'POST',
    //             headers: {
    //                 'Content-Type': 'application/json'
    //             },
    //             body: JSON.stringify({
    //                 content: userMessage,
    //                 session_id: sessionId
    //             })
    //         });

    //         if (!response.ok) {
    //             throw new Error('Lỗi kết nối server');
    //         }

    //         const data = await response.json();
            
    //         // Cập nhật session_id nếu server trả về mới (đề phòng)
    //         if (data.session_id) {
    //             sessionId = data.session_id;
    //             localStorage.setItem('chat_session_id', sessionId);
    //         }

    //         return data.content; // Trả về câu trả lời của bot

    //     } catch (error) {
    //         console.error('Lỗi:', error);
    //         return "Xin lỗi, không thể kết nối đến server.";
    //     }
    // }

// 3. Ví dụ cách dùng
// sendMessageToBot("Giá gói Basic là bao nhiêu?").then(reply => console.log(reply));
// Bạn có thể dùng đoạn mã JavaScript sau để nhúng vào UI bên ngoài của mình:
// Lưu ý: Đảm bảo rằng URL backendUrl trỏ đúng đến API của bạn, và rằng API của bạn chấp nhận CORS nếu frontend và backend không cùng domain.